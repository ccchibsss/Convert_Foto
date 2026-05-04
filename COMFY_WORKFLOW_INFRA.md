# ComfyUI workflow + local infrastructure

This repo now contains a runnable, configurable ComfyUI workflow plus a small local runner that can:
- install or point to models
- queue tasks via ComfyUI API
- manage conditional steps (refine pass, rerun-on-fail)
- apply macro overrides to presets
- generate a basic results report

This is designed for a Windows install at `F:\ComfyUI`.

---

## 1) Workflow overview

Workflow template (inpaint + optional refine pass):
- Load image + mask
- Encode for inpaint
- KSampler (main pass)
- Decode
- Optional refine pass (conditional)
- Save output

Files:
- `comfy/workflows/wmremove_template_prompt.json`
- `comfy/workflows/wmremove_template.meta.yaml`

The refine pass is controlled by preset or macro override.

---

## 2) Presets (tuned defaults)

Presets live in `configs/presets.yaml`:
- `fast`
- `balanced`
- `quality`
- `safe`

Each preset controls steps, cfg, denoise, sampler, prompt, and refine stage.

---

## 3) Macro overrides (global knobs)

Macro overrides are set in `configs/explorer.yaml` under `run.macro_overrides`.
These apply to any preset at runtime and let you quickly steer speed/quality.

Available macro params:
- `refine_enabled` (true/false/null)
- `steps_multiplier` (float, multiplies main + refine steps)
- `cfg_delta` (float, adds to cfg)
- `denoise_delta` (float, adds to denoise, clamped 0..1)
- `sampler` (override sampler name)
- `scheduler` (override scheduler name)
- `seed` (override seed)
- `prompt_append` (string appended to positive prompt)
- `prompt_neg_append` (string appended to negative prompt)

Example (faster, no refine):
```
run:
  preset: balanced
  macro_overrides:
    refine_enabled: false
    steps_multiplier: 0.75
    cfg_delta: -0.5
```

Example (push quality):
```
run:
  preset: balanced
  macro_overrides:
    refine_enabled: true
    steps_multiplier: 1.25
    cfg_delta: 0.5
    denoise_delta: 0.02
    prompt_append: "preserve micro details"
```

---

## 4) Conditional steps

Conditional logic is handled by the runner:
- **Refine pass** is enabled/disabled by preset or macro override.
- **Quality check** can be turned on/off in `configs/explorer.yaml`.
- **Rerun on fail** triggers a second pass with a different preset.

Config keys (in `configs/explorer.yaml`):
- `quality.enabled`
- `quality.fail_threshold`
- `quality.rerun_on_fail`
- `quality.rerun_preset`

---

## 5) Paths and ComfyUI

Set the ComfyUI input/output directories here:
- `configs/explorer.yaml` -> `paths.comfy_input_dir`
- `configs/explorer.yaml` -> `paths.comfy_output_dir`

For a Windows install at `F:\ComfyUI`:
- `F:/ComfyUI/input`
- `F:/ComfyUI/output`

---

## 6) Install models

Place your checkpoint in:
- `F:\ComfyUI\models\checkpoints`

Optional helper script (PowerShell):
```
.\scripts\install_models.ps1 -ComfyDir "F:\ComfyUI" -CheckpointName "sdxl_inpaint.safetensors" -ModelUrl "<direct_link_to_model>"
```

Then update `configs/presets.yaml` -> `ckpt` if you changed the filename.

---

## 7) Run ComfyUI

Start ComfyUI (Windows or WSL). Example:
```
python main.py --listen 127.0.0.1 --port 8188
```

Make sure it serves at `http://127.0.0.1:8188` (default in config).

---

## 8) Install local dependencies (Windows)

```
.\scripts\setup_venv.ps1
```

This creates a local virtualenv at `.venv` under the project directory.

---

## 9) Run tasks (Windows)

```
.\scripts\run_explorer.ps1
```

Outputs:
- results JSONL in `runs/<run_id>/results.jsonl`
- copy of output images in `outputs/<run_id>/`
- summary in `runs/<run_id>/summary.json`

Generate a report:
```
python tools/report.py --run runs/<run_id> --out runs/<run_id>/report.md
```

---

## 10) What you can tune

- Preset parameters (steps/cfg/denoise/sampler)
- Macro overrides for quick experiments
- Mask generation params (in `configs/explorer.yaml`)
- Quality thresholds + rerun behavior

---

## 11) File map

- `comfy/workflows/`   -> workflow template + meta
- `configs/`           -> presets and run config
- `tools/`             -> compiler, runner, metrics, quality
- `scripts/`           -> install + run helpers (PowerShell)
- `runs/`              -> logs and summaries
- `outputs/`           -> copied images
