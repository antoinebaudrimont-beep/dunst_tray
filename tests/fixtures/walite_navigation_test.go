// Opt-in fixture for Walite's rotating-ticket v2, in an isolated source tree.
// Adapted from whatsapp-terminal/walite, cmd/walite/linux_notification_manual_test.go,
// TestLinuxNotificationManualFixture (MIT, Copyright 2026 Antoine Baudrimont).
// Adds the production ticket receiver and content-free real-screen observation.
package main

import (
	"context"
	"errors"
	"fmt"
	"os"
	"os/exec"
	"os/signal"
	"path/filepath"
	"strings"
	"syscall"
	"testing"
	"time"

	"github.com/antoinebaudrimont-beep/walite/internal/tui"
	"github.com/gdamore/tcell/v2"
)

// This wrapper only records which synthetic body the actual terminal renders.
// It never observes a real account, ChatID, socket path or capability.
type navigationObservedScreen struct {
	tcell.Screen
	statePath string
	last      string
}

func (screen *navigationObservedScreen) Show() {
	screen.Screen.Show()
	width, height := screen.Size()
	var visible strings.Builder
	for y := 0; y < height; y++ {
		for x := 0; x < width; x++ {
			character, _, _, _ := screen.GetContent(x, y)
			visible.WriteRune(character)
		}
		visible.WriteByte('\n')
	}
	text := visible.String()
	state := "UNKNOWN"
	if strings.Contains(text, "SYNTHETIC-DIRECT-CONTENT") {
		state = "DIRECT"
	} else if strings.Contains(text, "SYNTHETIC-GROUP-CONTENT") {
		state = "GROUP"
	}
	if strings.Contains(text, "unsent-fixture-draft") {
		state += " DRAFT"
	}
	if state != screen.last {
		_ = os.WriteFile(screen.statePath, []byte(state), 0o600)
		screen.last = state
	}
}

func TestDunstTrayNavigationFixture(t *testing.T) {
	directory := os.Getenv("WALITE_TRAY_TEST_DIR")
	if directory == "" {
		t.Skip("requires explicit private fixture directory and real X11 terminal")
	}
	info, err := os.Stat(directory)
	if err != nil || !filepath.IsAbs(directory) || !info.IsDir() || info.Mode().Perm() != 0o700 {
		t.Fatal("fixture requires a private directory")
	}
	t.Setenv("XDG_CONFIG_HOME", filepath.Join(directory, "config"))
	t.Setenv("XDG_DATA_HOME", filepath.Join(directory, "data"))
	ctx, cancel := terminationContext(context.Background())
	defer cancel()
	capabilities := selectPlatformCapabilitiesWithOptions("linux", exec.LookPath, platformCapabilityOptions{
		notificationRunner:        runNotificationCommand,
		linuxNotificationIconPath: defaultLinuxNotificationIcon(),
		linuxActions: &linuxNotificationActionOptions{
			windowID: os.Getenv("WINDOWID"), x11: os.Getenv("DISPLAY") != "",
			run: func(ctx context.Context, command string, args []string) (string, error) {
				if filepath.Base(command) == "notify-send" {
					args = append([]string{"--hint=boolean:transient:true"}, args...)
				}
				return runLinuxNotificationCommand(ctx, command, args)
			},
		},
	})
	if capabilities.newLinuxNotificationActions == nil {
		t.Fatal("fixture requires Linux notification actions and WINDOWID")
	}
	receiver, err := newChatActivationReceiver(ctx)
	if err != nil {
		t.Fatal("receiver unavailable")
	}
	defer receiver.stop()
	actions, err := capabilities.newLinuxNotificationActions(ctx)
	if err != nil {
		t.Fatal("actions unavailable")
	}
	defer actions.stop()
	actions.bindChatActivation(receiver)
	triggers := make(chan os.Signal, 8)
	signal.Notify(triggers, syscall.SIGUSR1, syscall.SIGUSR2, syscall.SIGALRM)
	defer signal.Stop(triggers)
	producer, stop := context.WithCancel(ctx)
	done := make(chan struct{})
	go func() {
		defer close(done)
		for sequence := 1; ; sequence++ {
			select {
			case <-producer.Done():
				return
			case trigger := <-triggers:
				if trigger == syscall.SIGALRM {
					// Synthetic fault injection only: test actual server expiry
					// without changing production lifetime or waiting 24 hours.
					receiver.mu.Lock()
					for ticket, entry := range receiver.tickets {
						entry.expiresAt = time.Now().Add(-time.Second)
						receiver.tickets[ticket] = entry
					}
					receiver.mu.Unlock()
					_ = os.WriteFile(filepath.Join(directory, "expiry.ready"), []byte("expired"), 0o600)
					continue
				}
				id, label := "fixture-direct@lid", "Direct"
				if trigger == syscall.SIGUSR2 {
					id, label = "fixture-group@g.us", "Group"
				}
				_ = actions.Notify(producer, tui.Notification{
					ChatID: id, Title: "DunstTrayWaliteFixture: " + label,
					Body: fmt.Sprintf("Synthetic notification %d", sequence),
				})
			}
		}
	}()
	defer func() { stop(); <-done }()
	screen, err := tcell.NewScreen()
	if err != nil {
		t.Fatal("terminal unavailable")
	}
	if err := os.WriteFile(filepath.Join(directory, "fixture.pid"), []byte(fmt.Sprint(os.Getpid())), 0o600); err != nil {
		t.Fatal("fixture pid unavailable")
	}
	defer os.Remove(filepath.Join(directory, "fixture.pid"))
	if err := os.WriteFile(filepath.Join(directory, "fixture.window"), []byte(os.Getenv("WINDOWID")), 0o600); err != nil {
		t.Fatal("fixture window unavailable")
	}
	initial := tui.InitialState{Chats: []tui.InitialChat{
		{ID: "fixture-direct@lid", Title: "Fixture Direct", Messages: []tui.InitialMessage{
			{ID: "initial-direct", Text: "SYNTHETIC-DIRECT-CONTENT", BodyRetained: true, SentAt: time.Now()},
		}},
		{ID: "fixture-group@g.us", Title: "Fixture Group", IsGroup: true, Messages: []tui.InitialMessage{
			{ID: "initial-group", Text: "SYNTHETIC-GROUP-CONTENT", BodyRetained: true, SentAt: time.Now()},
		}},
	}}
	observed := &navigationObservedScreen{Screen: screen, statePath: filepath.Join(directory, "screen.state")}
	if err := tui.Run(ctx, observed, tui.Input{Options: tui.DefaultOptions(), InitialState: initial,
		ChatActivations: receiver.activations}); err != nil && !errors.Is(err, context.Canceled) {
		t.Fatal("fixture TUI failed")
	}
}
