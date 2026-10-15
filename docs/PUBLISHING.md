# Publishing checklist

Do not publish until the maintainer explicitly authorizes it.

1. Confirm the license and add `LICENSE`.
2. Complete the outstanding manual checks in `VALIDATION.md`.
3. Replace the screenshot placeholder with sanitized synthetic content.
4. Run tests and inspect `git status`, `git log`, and all tracked files.
5. Create an empty GitHub repository without generated files.
6. With explicit authorization, run:

   ```sh
   git remote add origin git@github.com:OWNER/dunst-tray.git
   git push -u origin main
   ```

Do not create a version tag until the documented milestone is implemented and
tested. A first stable tag is not implied by the current development version.

