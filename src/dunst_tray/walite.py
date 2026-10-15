"""Private Walite activation with one-use v1 and rotating v2 capabilities."""

from __future__ import annotations

import json
import os
import re
import socket
import stat
import struct
import time
from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class WaliteActivation:
    """An opaque per-notification capability. Never include it in diagnostics."""

    activation_socket: str = field(repr=False)
    activation_id: str = field(repr=False)
    version: int = field(default=1, repr=False)
    expires_at: int | None = field(default=None, repr=False)

    def record_json(self) -> str:
        data = {
            "version": self.version, "activation_socket": self.activation_socket,
            "activation_id": self.activation_id,
        }
        if self.version == 2:
            data["expires_at"] = self.expires_at
        return json.dumps(data, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class WaliteActivationResult:
    activation: WaliteActivation = field(repr=False)
    queued: bool


class WaliteActivationError(RuntimeError):
    """A deliberately redacted activation failure suitable for the UI."""


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate field")
        result[key] = value
    return result


def parse_activation(value) -> WaliteActivation | None:
    """Accept only documented v1/v2 hints; ignore unknown/malformed metadata."""
    if not isinstance(value, str):
        return None
    try:
        if len(value.encode("utf-8")) > 1024:
            return None
        data = json.loads(value, object_pairs_hook=_unique_object)
        if not isinstance(data, dict):
            return None
        version = data.get("version")
        if type(version) is not int or version not in (1, 2):
            return None
        keys = {"version", "activation_socket", "activation_id"}
        if version == 2:
            keys.add("expires_at")
            expiry = data.get("expires_at")
            if type(expiry) is not int or not 0 < expiry < 2**63:
                return None
        if set(data) != keys:
            return None
        endpoint, ticket = data["activation_socket"], data["activation_id"]
        if not isinstance(endpoint, str) or not isinstance(ticket, str):
            return None
        # Walite's documented private /tmp directory and socket namespace.
        # Do not allow traversal, alternate services, NUL/abstract sockets, or
        # paths beyond the producer's cross-platform 103-byte limit.
        if len(endpoint.encode("utf-8")) > 103 or not re.fullmatch(
            r"/tmp/walite-activation-[A-Za-z0-9_-]+/s-[A-Za-z0-9_-]+\.sock",
            endpoint,
        ):
            return None
        if not re.fullmatch(r"[0-9a-f]{64}", ticket):
            return None
        return WaliteActivation(endpoint, ticket, version, data.get("expires_at"))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None


class WaliteActivationClient:
    """Validate a private Unix peer; never retry/replay a consumed capability."""

    def __init__(self, timeout: float = 0.5):
        self.timeout = timeout

    @staticmethod
    def _validate_directory(info):
        if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o700):
            raise WaliteActivationError("Walite activation endpoint is not private.")

    @staticmethod
    def _validate_socket(info):
        if (not stat.S_ISSOCK(info.st_mode) or info.st_uid != os.geteuid()
                or stat.S_IMODE(info.st_mode) != 0o600):
            raise WaliteActivationError("Walite activation endpoint is not private.")

    def _open_endpoint(self, metadata):
        descriptor = None
        try:
            if not isinstance(metadata, WaliteActivation) or parse_activation(
                metadata.record_json()
            ) is None:
                raise WaliteActivationError("Invalid Walite discussion link.")
            directory, basename = os.path.split(metadata.activation_socket)
            descriptor = os.open(
                directory, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
            )
            self._validate_directory(os.fstat(descriptor))
            info = os.stat(basename, dir_fd=descriptor, follow_symlinks=False)
            self._validate_socket(info)
            return descriptor, basename, info
        except (OSError, ValueError, TypeError, WaliteActivationError):
            if descriptor is not None:
                os.close(descriptor)
            raise WaliteActivationError(
                "Walite discussion link is unavailable or not private."
            ) from None

    def availability(self, metadata) -> tuple[bool, str]:
        try:
            descriptor, _basename, _info = self._open_endpoint(metadata)
            os.close(descriptor)
            if (metadata.version == 2
                    and metadata.expires_at <= time.time()):
                return False, (
                    "Walite discussion link has expired. Show app is unchanged."
                )
            return True, (
                "Request this discussion in the running Walite instance. "
                "Walite may ignore requests while composing or showing a dialog."
            )
        except WaliteActivationError as error:
            return False, str(error)

    def send(self, metadata: WaliteActivation) -> WaliteActivationResult | None:
        """V2 acknowledges queue admission, not actual TUI selection."""
        deadline = time.monotonic() + self.timeout
        descriptor, basename, original = self._open_endpoint(metadata)
        try:
            if metadata.version == 2 and metadata.expires_at <= time.time():
                raise WaliteActivationError("Walite discussion link has expired.")
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
                connection.settimeout(self.timeout)
                # Pin the validated directory so renaming/replacing its path
                # cannot redirect the connection through a symlink race.
                connection.connect(f"/proc/self/fd/{descriptor}/{basename}")
                if not hasattr(socket, "SO_PEERCRED"):
                    raise WaliteActivationError("Peer verification unavailable.")
                _pid, uid, _gid = struct.unpack("3i", connection.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i"),
                ))
                if uid != os.geteuid():
                    raise WaliteActivationError("Peer verification failed.")
                self._validate_directory(os.fstat(descriptor))
                current = os.stat(basename, dir_fd=descriptor, follow_symlinks=False)
                self._validate_socket(current)
                if (current.st_dev, current.st_ino) != (
                    original.st_dev, original.st_ino,
                ):
                    raise WaliteActivationError("Endpoint identity changed.")
                payload = json.dumps({
                    "version": metadata.version,
                    "activation_id": metadata.activation_id,
                }, separators=(",", ":")).encode("utf-8")
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise WaliteActivationError("Walite request timed out.")
                connection.settimeout(remaining)
                connection.sendall(payload)
                connection.shutdown(socket.SHUT_WR)
                if metadata.version == 2:
                    return self._read_rotation(connection, metadata, deadline)
                # V1 never reads a response. No retries/launch/fallback in either.
        except WaliteActivationError:
            raise
        except (OSError, ValueError, TypeError, RecursionError):
            raise WaliteActivationError(
                "Could not send the Walite discussion request."
            ) from None
        finally:
            os.close(descriptor)

    @staticmethod
    def _read_rotation(connection, metadata, deadline):
        data = bytearray()
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise WaliteActivationError("Walite response timed out.")
            connection.settimeout(remaining)
            chunk = connection.recv(1025 - len(data))
            if not chunk:
                break
            data.extend(chunk)
            if len(data) > 1024:
                raise WaliteActivationError("Invalid Walite response.")
        value = json.loads(bytes(data).decode("utf-8"),
                           object_pairs_hook=_unique_object)
        if (not isinstance(value, dict) or type(value.get("version")) is not int
                or value["version"] != 2):
            raise WaliteActivationError("Invalid Walite response.")
        if value == {"version": 2, "status": "unavailable"}:
            raise WaliteActivationError(
                "Walite discussion link is unavailable. It may have expired."
            )
        if (set(value) != {"version", "status", "activation_id", "expires_at"}
                or value["status"] not in ("queued", "busy")):
            raise WaliteActivationError("Invalid Walite response.")
        renewed = parse_activation(json.dumps({
            "version": 2, "activation_socket": metadata.activation_socket,
            "activation_id": value["activation_id"],
            "expires_at": value["expires_at"],
        }))
        if (renewed is None or renewed.activation_id == metadata.activation_id
                or renewed.expires_at != metadata.expires_at
                or renewed.expires_at <= time.time()):
            raise WaliteActivationError("Invalid Walite ticket rotation.")
        return WaliteActivationResult(renewed, value["status"] == "queued")
