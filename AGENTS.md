<!-- rtk-instructions v2 -->
# RTK (Rust Token Killer) - Token-Optimized Commands

## Golden Rule

**Always prefix commands with `rtk`**. If RTK has a dedicated filter, it uses it. If not, it passes through unchanged. This means RTK is always safe to use.

**Important**: Even in command chains with `&&`, use `rtk`:
```bash
# ❌ Wrong
git add . && git commit -m "msg" && git push

# ✅ Correct
rtk git add . && rtk git commit -m "msg" && rtk git push
```

## RTK Commands by Workflow

### Build & Compile (80-90% savings)
```bash
rtk cargo build         # Cargo build output
rtk cargo check         # Cargo check output
rtk cargo clippy        # Clippy warnings grouped by file (80%)
rtk tsc                 # TypeScript errors grouped by file/code (83%)
rtk lint                # ESLint/Biome violations grouped (84%)
rtk prettier --check    # Files needing format only (70%)
rtk next build          # Next.js build with route metrics (87%)
```

### Test (60-99% savings)
```bash
rtk cargo test          # Cargo test failures only (90%)
rtk go test             # Go test failures only (90%)
rtk jest                # Jest failures only (99.5%)
rtk vitest              # Vitest failures only (99.5%)
rtk playwright test     # Playwright failures only (94%)
rtk pytest              # Python test failures only (90%)
rtk rake test           # Ruby test failures only (90%)
rtk rspec               # RSpec test failures only (60%)
rtk test <cmd>          # Generic test wrapper - failures only
```

### Git (59-80% savings)
```bash
rtk git status          # Compact status
rtk git log             # Compact log (works with all git flags)
rtk git diff            # Compact diff (80%)
rtk git show            # Compact show (80%)
rtk git add             # Ultra-compact confirmations (59%)
rtk git commit          # Ultra-compact confirmations (59%)
rtk git push            # Ultra-compact confirmations
rtk git pull            # Ultra-compact confirmations
rtk git branch          # Compact branch list
rtk git fetch           # Compact fetch
rtk git stash           # Compact stash
rtk git worktree        # Compact worktree
```

Note: Git passthrough works for ALL subcommands, even those not explicitly listed.

### GitHub (26-87% savings)
```bash
rtk gh pr view <num>    # Compact PR view (87%)
rtk gh pr checks        # Compact PR checks (79%)
rtk gh run list         # Compact workflow runs (82%)
rtk gh issue list       # Compact issue list (80%)
rtk gh api              # Compact API responses (26%)
```

### JavaScript/TypeScript Tooling (70-90% savings)
```bash
rtk pnpm list           # Compact dependency tree (70%)
rtk pnpm outdated       # Compact outdated packages (80%)
rtk pnpm install        # Compact install output (90%)
rtk npm run <script>    # Compact npm script output
rtk npx <cmd>           # Compact npx command output
rtk prisma              # Prisma without ASCII art (88%)
```

### Files & Search (60-75% savings)
```bash
rtk ls <path>           # Tree format, compact (65%)
rtk read <file>         # Code reading with filtering (60%)
rtk grep <pattern>      # Search grouped by file (75%). Format flags (-c, -l, -L, -o, -Z) run raw.
rtk find <pattern>      # Find grouped by directory (70%)
```

### Analysis & Debug (70-90% savings)
```bash
rtk err <cmd>           # Filter errors only from any command
rtk log <file>          # Deduplicated logs with counts
rtk json <file>         # JSON structure without values
rtk deps                # Dependency overview
rtk env                 # Environment variables compact
rtk summary <cmd>       # Smart summary of command output
rtk diff                # Ultra-compact diffs
```

### Infrastructure (85% savings)
```bash
rtk docker ps           # Compact container list
rtk docker images       # Compact image list
rtk docker logs <c>     # Deduplicated logs
rtk kubectl get         # Compact resource list
rtk kubectl logs        # Deduplicated pod logs
```

### Network (65-70% savings)
```bash
rtk curl <url>          # Compact HTTP responses (70%)
rtk wget <url>          # Compact download output (65%)
```

### Meta Commands
```bash
rtk gain                # View token savings statistics
rtk gain --history      # View command history with savings
rtk discover            # Analyze Claude Code sessions for missed RTK usage
rtk proxy <cmd>         # Run command without filtering (for debugging)
rtk init                # Add RTK instructions to CLAUDE.md
rtk init --global       # Add RTK to ~/.claude/CLAUDE.md
```

## Token Savings Overview

| Category | Commands | Typical Savings |
|----------|----------|-----------------|
| Tests | vitest, playwright, cargo test | 90-99% |
| Build | next, tsc, lint, prettier | 70-87% |
| Git | status, log, diff, add, commit | 59-80% |
| GitHub | gh pr, gh run, gh issue | 26-87% |
| Package Managers | pnpm, npm, npx | 70-90% |
| Files | ls, read, grep, find | 60-75% |
| Infrastructure | docker, kubectl | 85% |
| Network | curl, wget | 65-70% |

Overall average: **60-90% token reduction** on common development operations.
<!-- /rtk-instructions -->

# AGENTS.md - Developer Agent Guide for Eaubbies

Welcome, developer agent! This repository contains **Eaubbies**, a Home Assistant Add-on that captures water meter images via an RTSP camera feed (e.g., Tapo), applies image preprocessing (OpenCV/scikit-image), and digitizes/reads the value using **Azure Computer Vision API (OCR)**. It then publishes the readings to Home Assistant via **MQTT**.

---

## 🛠️ Essential Commands

The project uses [uv](https://docs.astral.sh/uv/) for Python dependency and workspace management.

### Local Development
```bash
# Navigate to the Python source directory
cd eaubbies/src

# Start the Flask development server with hot-reload
uv run -- flask run --debug
```

### Build & Deploy Commands
*   **Local Docker Build:**
    ```bash
    cd eaubbies
    docker build --build-arg BUILD_FROM="homeassistant/amd64-base-debian:bookworm" -t eaubbies:local .
    ```
*   **Docker Compose Startup:**
    ```bash
    # Run only eaubbies container (port 8099)
    docker compose up
    
    # Run eaubbies AND a local Home Assistant instance (port 8123)
    docker compose --profile all up
    ```
*   **Home Assistant Add-on Build:**
    ```bash
    docker run --rm --privileged \
      -v ~/.docker:/root/.docker -v .:/data \
      ghcr.io/home-assistant/amd64-builder:latest \
      --all -t /data/eaubbies
    ```

---

## 🏗️ Architecture & Component Flow

The add-on runs **Gunicorn** behind **Nginx** inside the container, managed by **Supervisor**.

```
                           +------------------------+
                           |  RTSP Camera / Video   |
                           +-----------+------------+
                                       | (cv2.VideoCapture)
                                       v
+------------------+       +-----------+------------+       +---------------------+
|   Flask UI /     | <---->|      service.py        | <---> | Azure AI Vision API |
|   Web Server     |       | (create_improved_frame)|       |    (OCR Reader)     |
+------------------+       +-----------+------------+       +---------------------+
                                       |
                                       v (total_liters, left_number, right_number)
                           +-----------+------------+
                           |  MQTT Publish Client   |
                           +-----------+------------+
                                       |
                                       v (Home Assistant Discovery Prefix)
                           +-----------+------------+
                           |   Home Assistant /     |
                           |   MQTT Broker (Mosquitto)|
                           +------------------------+
```

### Key Modules:
1.  **`app.py`:** Flask web application. Exposes web routes for live camera calibration (`/video_feed`), manual configurations, image alignment/coordinates editing, manual processing, and initial onboarding setup (`/init`).
2.  **`service.py`:** Main control flow. Orchestrates RTSP image capture, OpenCV preprocessing steps, Azure Computer Vision OCR calls, decimal alignment, and MQTT sensor updates.
3.  **`cron.py`:** Runs on a scheduled basis (configured via `crontab`) to trigger `service_process(increase_cron_count=True)` automatically at scheduled times.
4.  **`utils/rtsp_client.py`:** Wraps OpenCV (`cv2`) and `scikit-image` preprocessing. Includes image rotating, sharpening, contrast/exposure tuning, blurring, cropping, and background blanking around OCR detection boxes (unsharp masking, adaptive thresholding).
5.  **`utils/azure_client.py`:** Connects to Microsoft Azure Cognitive Services (Computer Vision) SDK `ComputerVisionClient` to perform OCR in the cloud.
6.  **`utils/configuration.py`:** Loads and persists runtime configuration parameters inside `eaubbies/src/data/config/main.yaml` (autogenerated at startup with sensible defaults if missing).
7.  **`utils/mqtt.py`:** Manages MQTT connections, Home Assistant self-discovery config payload registration, and state updates under the configured discovery topic.

---

## ⚙️ Configuration Schema

The application stores settings inside a YAML file: `data/config/main.yaml` (relative to the `src` folder).

### Default Structure Reference:
*   **`frame`**: Storage paths for raw, improved, and bounding-boxed images (`static/img/frames`).
*   **`vision`**: Configuration for digits mapping (integer vs. decimal counts), bounding box coordinates, and rotation offsets (`rotate`).
*   **`rtsp`**: Stream URL and image enhancement switches (contrast, sharpening, exposure thresholds, and region of interest fills).
*   **`mqtt`**: Broker credentials, Home Assistant entity naming config, unique device IDs, and sensor definitions.

---

## ⚡ Gotchas & Implicit Conventions

When modifying this repository, be extremely careful of the following patterns:

*   **Poetry vs. UV:** The project uses `uv` in local development and inside the Dockerfile. The cron script path command has been modernized from poetry to uv in the code:
    `command = "/app/.venv/bin/python /app/cron.py"`
*   **Local tests:** A local unit test suite using `pytest` is configured in `tests/`. It can be run from the root or inside the `eaubbies/src` folder:
    `uv run pytest ../../tests/`
*   **Dual OCR Engines:** Supports both Azure Computer Vision (cloud-based) and Tesseract OCR (local/container-based) via `vision.engine` config parameter.
*   **Home Assistant Add-on Lifecycle:** The entrypoint script (`entrypoint.sh` -> `0.sh`) spins up supervisord, which starts Gunicorn serving the Unix socket `/app/ipc.sock`, and Nginx proxies incoming traffic from Port `8099` to Gunicorn.
*   **CV2 Image Layouts:** Color format adjustments (RGB vs. BGR vs. Gray) inside `service.py` and `rtsp_client.py` must match Azure Vision constraints (which accepts JPEG binary byte streams).
*   **Coordinate Math:** The region selection overlays on the web UI might output offsets that require padding adjustments in `service.py:97-99` (e.g., `- 50` on Y/height to capture full characters).
*   **Initial Setup Flow:** If the setting `setup.init_config` is `False`, the web UI routes all incoming calls `/` or `/index` to `/init`.


## Code Style & Linting

Strict linting is enforced in CI. **Always run formatters before submitting changes.**

- **Python**: `black` (formatting), `flake8` (linting), `ruff` (linting).
- **JavaScript**: `prettier`.
- **Shell**: `shellcheck`.
- **Docker**: `hadolint`.
- **JSON**: `jq` validation.

# Workflow Orchestration
## 1. Plan Node Default
- Enter plan mode for ANY non-trivial task (3+ steps or architectural decisions)
- If something goes sideways, STOP and re-plan immediately - don't keep pushing
- Use plan mode for verification steps, not just building
- Write detailed specs upfront to reduce ambiguity

## 2. Subagent Strategy
- Use subagents liberally to keep main context window clean
- Offload research, exploration, and parallel analysis to subagents
- For complex problems, throw more compute at it via subagents
- One tack per subagent for focused execution

## 3. Self-Improvement Loop
- After ANY correction from the user: update '.crush/tasks/lessons.md with the pattern
- Write rules for yourself that prevent the same mistake
- Ruthlessly iterate on these lessons until mistake rate drops
- Review lessons at session start for relevant project

## 4. Verification Before Done
- Never mark a task complete without proving it works
- Diff behavior between main and your changes when relevant
- Ask yourself: "Would a staff engineer approve this?"
- Run tests, check logs, demonstrate correctness

## 5. Demand Elegance (Balanced)
- For non-trivial changes: pause and ask "is there a more elegant way?"
- If a fix feels hacky: "Knowing everything I know now, implement the elegant solution"
- Skip this for simple, obvious fixes - don't over-engineer
- Challenge your own work before presenting it
## 6. Autonomous Bug Fixing
- When given a bug report: just fix it. Don't ask for hand-holding
- Point at logs, errors, failing tests - then resolve them
- Zero context switching required from the user
- Go fix failing CI tests without being told how

## Task Management
1. **Plan First**: Write plan to '.crush/tasks/todo.md' with checkable items
2. **Verify Plan**: Check in before starting implementation
3. **Track Progress**: Mark items complete as you go
4. **Explain Changes**: High-level summary at each step
5. **Document Results**: Add review section to .crush/tasks/todo.md
6. **Capture Lessons**: Update '.crush/tasks/lessons.md after corrections

## Core Principles
- **Simplicity First**: Make every change as simple as possible. Impact minimal code.
- **No Laziness**: Find root causes. No temporary fixes. Senior developer standards.
- **Minimal Impact**: Changes should only touch what's necessary. Avoid introducing bugs.

## Thinking
For every complex problem:

1. Decompose: Break into sub-problems
2. Solve: Address each with explicit confidence (0.0-1.0)
3. Verify: check logic, facts, completeness, bias
4. Synthesize: combine using weighted confidence
5. Reflect: If confidence <0.8, identify weakness and retry

## Output
- Always answer in english
- The code generated should be formatted with black and flake8 should return 0 errors.
- Always include error handling
- Always include testing
- Always comment the function and the class
- Always include the path of the file in a comment when a new one is created at the beginning of the file for python
- After writing the proposed solution , identify 3 potentials bugs or edge case in your solution. Then rewrite the solution to resolve those issues.
- Always output: Clear answer. Confidence level. Key caveats
- Always give the full class, function, or file and not just the line to change or a portion of code, except if instructed otherwise
- Always ask a question if you need additional information