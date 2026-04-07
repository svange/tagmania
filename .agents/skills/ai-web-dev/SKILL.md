---
name: ai-web-dev
description: Browse websites and inspect web UIs during development. Guides you to the right browser tool (WebFetch, agent-browser, playwright-cli) based on what you need.
argument-hint: "[url or task description]"
---

Browse or inspect a web page for development purposes: $ARGUMENTS

Decision-tree skill for web development tasks. Picks the lightest tool that fits.

## Usage Examples
- `/ai-web-dev https://localhost:3000` - Check what the local dev server shows
- `/ai-web-dev screenshot https://example.com` - Take a screenshot
- `/ai-web-dev debug network on https://api.example.com` - Inspect network requests
- `/ai-web-dev what does our landing page look like` - Visual check

## 1. Decide What You Need

Analyze $ARGUMENTS and classify the task:

| Need | Tool | Why |
|------|------|-----|
| Read page content / docs | **WebFetch** | Zero setup, minimal context |
| Search the web for info | **WebSearch** | Built-in, no browser needed |
| See what a page looks like | **agent-browser screenshot** | Annotated screenshots with element labels |
| Inspect/interact with DOM | **agent-browser snapshot** | Compact refs (@e1, @e2), lowest context |
| Click, fill forms, navigate | **agent-browser** | Ref-based interaction, efficient |
| Network request inspection | **playwright-cli** | Has network interception |
| Multi-browser testing | **playwright-cli** | Supports Chromium, Firefox, WebKit |
| Console errors / JS debugging | **playwright-cli** | Has console capture |
| Record a test / generate code | **playwright-cli codegen** | Test generation built-in |

**Default rule**: Start with the lightest tool. Escalate only if it can't do what you need.

## 2. Tier 1: WebSearch / WebFetch (Built-in)

Use when you just need to read content or search for information.
These are already available -- no setup needed.

```
# Search the web
Use the WebSearch tool directly

# Fetch and read a specific URL
Use the WebFetch tool directly
```

**When to escalate to Tier 2**: You need to see the rendered page, interact with elements, or WebFetch is blocked/insufficient.

## 3. Tier 2: agent-browser (Primary Browser Tool)

Use for most interactive browser tasks. Returns compact element refs.

### Quick snapshot (see what's on the page)
```bash
agent-browser navigate "https://localhost:3000"
agent-browser snapshot -i   # -i = interactive elements only
```

Output looks like:
```
@e1 [header]
  @e3 [a] "Home"
  @e6 [button] "Sign In"
@e7 [main]
  @e10 [input type="email"] placeholder="Email"
  @e12 [button type="submit"] "Log In"
```

### Take a screenshot
```bash
agent-browser screenshot /tmp/page.png
agent-browser screenshot /tmp/page.png --annotate   # numbered labels on elements
```

### Interact with elements (use refs from snapshot)
```bash
agent-browser click @e6              # Click "Sign In"
agent-browser fill @e10 "user@test.com"  # Fill email field
agent-browser select @e15 "option-value"  # Select dropdown
agent-browser snapshot -i            # Re-snapshot after interaction
```

### Scoped/filtered snapshots (reduce context)
```bash
agent-browser snapshot -i -s "#main"        # Only elements inside #main
agent-browser snapshot -i -d 3              # Max depth 3
agent-browser snapshot -i -c                # Compact format
agent-browser snapshot --json               # Structured JSON output
```

### Extract text content
```bash
agent-browser execute "document.body.innerText"
```

**When to escalate to Tier 3**: You need network interception, console logs, multi-browser testing, or Playwright-specific features.

## 4. Tier 3: playwright-cli (Advanced)

Use for complex automation, debugging, and cross-browser testing.

### Navigate and snapshot
```bash
playwright-cli navigate "https://localhost:3000"
playwright-cli snapshot    # Saves YAML to .playwright-cli/
```

### Interact (uses refs without @ prefix)
```bash
playwright-cli click e15
playwright-cli fill e5 "text"
playwright-cli screenshot --filename page.png
```

### Network inspection
```bash
playwright-cli network-log start
playwright-cli navigate "https://api.example.com"
playwright-cli network-log stop    # Shows all requests/responses
```

### Console capture
```bash
playwright-cli console start
playwright-cli navigate "https://localhost:3000"
playwright-cli console stop        # Shows console.log, errors, warnings
```

### Multi-browser testing
```bash
playwright-cli --browser firefox navigate "https://localhost:3000"
playwright-cli --browser webkit navigate "https://localhost:3000"
```

### Generate test code from actions
```bash
playwright-cli codegen "https://localhost:3000"
```

## 5. Common Web Dev Workflows

### "Check if my local dev server is working"
```bash
agent-browser navigate "http://localhost:3000"
agent-browser screenshot /tmp/dev-check.png
agent-browser snapshot -i
```

### "Debug why the login form isn't working"
```bash
agent-browser navigate "http://localhost:3000/login"
agent-browser snapshot -i -s "form"
# Try filling and submitting
agent-browser fill @e10 "test@example.com"
agent-browser fill @e11 "password123"
agent-browser click @e12
# Check result
agent-browser snapshot -i
agent-browser screenshot /tmp/after-login.png
```

### "Check what API calls a page makes"
```bash
playwright-cli network-log start
playwright-cli navigate "http://localhost:3000/dashboard"
playwright-cli network-log stop
```

### "See console errors on a page"
```bash
playwright-cli console start
playwright-cli navigate "http://localhost:3000"
playwright-cli console stop
```

### "Compare rendering across browsers"
```bash
playwright-cli --browser chromium screenshot --filename /tmp/chrome.png
playwright-cli --browser firefox screenshot --filename /tmp/firefox.png
playwright-cli --browser webkit screenshot --filename /tmp/safari.png
```

## 6. Troubleshooting

- **"Browser not found"**: Run `agent-browser install` or `playwright-cli install-browser`
- **"Navigation timeout"**: Page might be down. Check with `curl -I <url>` first.
- **"No sandbox"**: Already configured via `CHROME_NO_SANDBOX=1`. If issues persist, pass `--no-sandbox` explicitly.
- **Stale refs**: Refs (@e1, e5) invalidate on page change. Always re-snapshot after navigation or interaction.
- **High context usage**: Use `-i` (interactive only), `-s` (scoped), `-d` (depth limit) to reduce snapshot size.
