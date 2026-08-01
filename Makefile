# Build macOS .app + zip using system python3 (no venv) — same pattern as statsinfo.
# One-time: pip3 install -r requirements-build.txt
# (use PySide6-Essentials only — not full PySide6 / Addons)

APP_NAME = AppUnload
VERSION = 0.1.0
ZIP = dist/AppUnload-$(VERSION)-macos.zip
PYTHON ?= python3

.PHONY: app zip release clean-dist help strip-qt

help:
	@echo "Targets:"
	@echo "  make app         - build dist/$(APP_NAME).app (py2app + Qt strip)"
	@echo "  make zip         - zip the .app for sharing"
	@echo "  make release     - app + zip"
	@echo "  make clean-dist  - remove build/ and dist/"

# Build .app with py2app
# py2app forbids install_requires; setuptools would inject them from pyproject.toml,
# so we move that file aside for the build only.
app:
	rm -rf build dist
	@mv pyproject.toml pyproject.toml.bak
	@status=0; \
	$(PYTHON) setup.py py2app || status=$$?; \
	mv -f pyproject.toml.bak pyproject.toml; \
	exit $$status
	$(PYTHON) scripts/strip_pyside_bundle.py "dist/$(APP_NAME).app"
	@# Ad-hoc sign so local Gatekeeper is less noisy; Developer ID still needed for notarized downloads.
	codesign --force --deep --sign - "dist/$(APP_NAME).app" 2>/dev/null || true
	@echo "Bundle ID: $$(/usr/libexec/PlistBuddy -c 'Print :CFBundleIdentifier' 'dist/$(APP_NAME).app/Contents/Info.plist')"
	@du -sh "dist/$(APP_NAME).app"
	@echo "Built: dist/$(APP_NAME).app"

strip-qt:
	@test -d "dist/$(APP_NAME).app" || (echo "Missing dist/$(APP_NAME).app — run: make app"; exit 1)
	$(PYTHON) scripts/strip_pyside_bundle.py "dist/$(APP_NAME).app"
	codesign --force --deep --sign - "dist/$(APP_NAME).app" 2>/dev/null || true
	@du -sh "dist/$(APP_NAME).app"

# Zip existing .app for sharing
zip:
	@test -d "dist/$(APP_NAME).app" || (echo "Missing dist/$(APP_NAME).app — run: make app"; exit 1)
	cd dist && rm -f "AppUnload-$(VERSION)-macos.zip" && \
		zip -ry "AppUnload-$(VERSION)-macos.zip" "$(APP_NAME).app"
	@ls -lh "$(ZIP)"

# Full distribute: .app + zip
release: app zip
	@echo ""
	@echo "Ready to distribute:"
	@echo "  App: $(CURDIR)/dist/$(APP_NAME).app"
	@echo "  Zip: $(CURDIR)/$(ZIP)"
	@echo "  Note: ad-hoc signed only. For Gatekeeper-clean downloads, codesign + notarize with a Developer ID."

clean-dist:
	rm -rf build dist
