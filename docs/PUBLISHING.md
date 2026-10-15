# Publishing checklist

Do not publish until the maintainer explicitly authorizes it.

1. Complete the outstanding manual checks in `VALIDATION.md`.
2. Replace the screenshot placeholder with sanitized synthetic content.
3. Run tests and inspect `git status`, `git log`, and all tracked files.
4. Create an empty GitHub repository without generated files.
5. With explicit authorization, run:

   ```sh
   git remote add origin git@github.com:OWNER/dunst-tray.git
   git push -u origin main
   ```

Do not create a version tag until the documented milestone is implemented and
tested. A first stable tag is not implied by the current development version.

