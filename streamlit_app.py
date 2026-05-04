from __future__ import annotations

import html
import time
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st
from PIL import Image
from tools.streamlit_image_gallery import create_thumbnail, render_image_gallery
from tools.project_backend import (  # noqa: E402
    calculate_project_masks,
    choose_image_ids,
    ensure_project,
    export_project,
    index_project_images,
    list_project_runs,
    project_paths,
    run_project_batch,
)
from tools.project_snapshot_service import build_project_snapshot, load_repeat_family_library
from wmr.jsonio import LoadIssue, format_load_issues, read_json_file, read_jsonl_file

ROOT = Path(__file__).resolve().parent


st.set_page_config(
    page_title="wmRemove Project Workspace",
    page_icon="W",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    .wmr-status-wrap {
        position: sticky;
        top: 0.25rem;
        z-index: 40;
        background: linear-gradient(135deg, #f7f3eb 0%, #fffdf9 100%);
        border: 1px solid #d8cbb8;
        border-radius: 18px;
        padding: 0.9rem 1rem;
        box-shadow: 0 10px 24px rgba(56, 42, 18, 0.08);
        margin-bottom: 0.35rem;
    }
    .wmr-status-grid {
        display: grid;
        grid-template-columns: repeat(5, minmax(0, 1fr));
        gap: 0.75rem;
        margin-bottom: 0.5rem;
    }
    .wmr-status-card {
        background: rgba(255, 255, 255, 0.76);
        border: 1px solid #e6dccd;
        border-radius: 12px;
        padding: 0.55rem 0.7rem;
    }
    .wmr-status-label {
        display: block;
        font-size: 0.72rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #7f6f5a;
        margin-bottom: 0.2rem;
    }
    .wmr-status-value {
        display: block;
        font-size: 1rem;
        color: #201a14;
        font-weight: 600;
        line-height: 1.2;
    }
    .wmr-status-pill {
        display: inline-block;
        padding: 0.12rem 0.5rem;
        border-radius: 999px;
        font-size: 0.82rem;
        font-weight: 700;
    }
    .wmr-status-idle { background: #ece6da; color: #5d5244; }
    .wmr-status-running { background: #d7eadf; color: #175a38; }
    .wmr-status-complete { background: #d8e7f8; color: #1d4f83; }
    .wmr-status-error { background: #f5d9d4; color: #8a2f25; }
    .wmr-status-message {
        font-size: 0.98rem;
        color: #201a14;
        font-weight: 600;
        margin-bottom: 0.25rem;
    }
    .wmr-status-path {
        font-family: Consolas, monospace;
        font-size: 0.85rem;
        color: #5d5244;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
    }
    .wmr-status-feed {
        border: 1px solid #e6dccd;
        border-radius: 14px;
        background: rgba(255, 255, 255, 0.72);
        padding: 0.75rem 0.9rem;
        margin-bottom: 1rem;
    }
    .wmr-status-feed-title {
        font-size: 0.78rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #7f6f5a;
        margin-bottom: 0.45rem;
    }
    .wmr-status-feed-line {
        font-family: Consolas, monospace;
        font-size: 0.84rem;
        color: #3b3128;
        margin-bottom: 0.18rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def resolve_path(value: str) -> Path:
    return Path(value).expanduser().resolve()


def read_json(
    path: Path,
    default: Any,
    issues: list[LoadIssue] | None = None,
    source: str | None = None,
) -> Any:
    return read_json_file(path, default, issues=issues, source=source)


def read_jsonl(
    path: Path,
    issues: list[LoadIssue] | None = None,
    source: str | None = None,
) -> list[dict[str, Any]]:
    return read_jsonl_file(path, issues=issues, source=source)


def format_percent(value: Any, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}%}"
    except Exception:
        return "-"


def format_float(value: Any, digits: int = 3) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "-"


STATUS_HISTORY_LIMIT = 10


def init_status_state() -> None:
    st.session_state.setdefault(
        "wmr_status",
        {
            "state": "idle",
            "phase": "idle",
            "message": "Idle",
            "image": "",
            "current": 0,
            "total": 0,
            "progress": 0.0,
            "updated_at": time.strftime("%H:%M:%S"),
            "score": None,
            "detector": None,
            "calls": None,
            "note": "",
        },
    )
    st.session_state.setdefault("wmr_status_history", [])


def append_status_history(payload: dict[str, Any]) -> None:
    image = str(payload.get("image") or "-")
    current = int(payload.get("current") or 0)
    total = int(payload.get("total") or 0)
    queue = f"{current}/{total}" if total else "-"
    parts = [payload.get("updated_at", time.strftime("%H:%M:%S")), str(payload.get("phase") or "idle"), queue, image]
    if payload.get("note"):
        parts.append(str(payload["note"]))
    if payload.get("score") is not None:
        parts.append(f"score={format_float(payload['score'])}")
    if payload.get("detector") is not None:
        parts.append(f"det={format_float(payload['detector'])}")
    entry = " | ".join(parts)
    history: list[str] = st.session_state["wmr_status_history"]
    if not history or history[-1] != entry:
        history.append(entry)
        del history[:-STATUS_HISTORY_LIMIT]


def render_status_panel() -> None:
    payload = st.session_state["wmr_status"]
    history: list[str] = st.session_state["wmr_status_history"]
    state = str(payload.get("state") or "idle")
    current = int(payload.get("current") or 0)
    total = int(payload.get("total") or 0)
    queue = f"{current}/{total}" if total else "-"
    progress_value = float(payload.get("progress") or 0.0)
    score_value = format_float(payload.get("score")) if payload.get("score") is not None else "-"
    detector_value = format_float(payload.get("detector")) if payload.get("detector") is not None else "-"
    calls_value = str(payload.get("calls")) if payload.get("calls") is not None else "-"
    status_bar_placeholder.markdown(
        f"""
        <div class="wmr-status-wrap">
            <div class="wmr-status-grid">
                <div class="wmr-status-card">
                    <span class="wmr-status-label">State</span>
                    <span class="wmr-status-value">
                        <span class="wmr-status-pill wmr-status-{html.escape(state)}">{html.escape(state)}</span>
                    </span>
                </div>
                <div class="wmr-status-card">
                    <span class="wmr-status-label">Phase</span>
                    <span class="wmr-status-value">{html.escape(str(payload.get("phase") or "-"))}</span>
                </div>
                <div class="wmr-status-card">
                    <span class="wmr-status-label">Queue</span>
                    <span class="wmr-status-value">{html.escape(queue)}</span>
                </div>
                <div class="wmr-status-card">
                    <span class="wmr-status-label">Pool Calls</span>
                    <span class="wmr-status-value">{html.escape(calls_value)}</span>
                </div>
                <div class="wmr-status-card">
                    <span class="wmr-status-label">Quality / Detector</span>
                    <span class="wmr-status-value">{html.escape(score_value)} / {html.escape(detector_value)}</span>
                </div>
            </div>
            <div class="wmr-status-message">{html.escape(str(payload.get("message") or ""))}</div>
            <div class="wmr-status-path">{html.escape(str(payload.get("image") or "-"))}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    status_progress_placeholder.progress(progress_value, text=f"{payload.get('updated_at', '-')}: {payload.get('message', '')}")
    if history:
        lines = "".join(f'<div class="wmr-status-feed-line">{html.escape(line)}</div>' for line in reversed(history))
        status_history_placeholder.markdown(
            f'<div class="wmr-status-feed"><div class="wmr-status-feed-title">Recent Activity</div>{lines}</div>',
            unsafe_allow_html=True,
        )
    else:
        status_history_placeholder.markdown(
            '<div class="wmr-status-feed"><div class="wmr-status-feed-title">Recent Activity</div><div class="wmr-status-feed-line">No activity yet.</div></div>',
            unsafe_allow_html=True,
        )


def set_status(
    *,
    state: str,
    phase: str,
    message: str,
    image: str = "",
    current: int | None = None,
    total: int | None = None,
    progress: float | None = None,
    score: Any = None,
    detector: Any = None,
    calls: Any = None,
    note: str = "",
    log: bool = True,
) -> None:
    payload = dict(st.session_state["wmr_status"])
    payload.update(
        {
            "state": state,
            "phase": phase,
            "message": message,
            "image": image,
            "updated_at": time.strftime("%H:%M:%S"),
            "score": score,
            "detector": detector,
            "calls": calls,
            "note": note,
        }
    )
    if current is not None:
        payload["current"] = int(current)
    if total is not None:
        payload["total"] = int(total)
    if progress is None:
        total_value = int(payload.get("total") or 0)
        current_value = int(payload.get("current") or 0)
        progress = min(current_value / total_value, 1.0) if total_value > 0 else float(payload.get("progress") or 0.0)
    payload["progress"] = max(0.0, min(float(progress), 1.0))
    st.session_state["wmr_status"] = payload
    if log:
        append_status_history(payload)
    render_status_panel()


def build_mask_overlay(source_value: Any, mask_value: Any, alpha: int = 160) -> Image.Image | None:
    source_path = Path(str(source_value))
    mask_path = Path(str(mask_value))
    if not source_path.exists() or not mask_path.exists():
        return None
    try:
        with Image.open(source_path) as source_handle:
            source = source_handle.convert("RGBA")
        with Image.open(mask_path) as mask_handle:
            mask = mask_handle.convert("L")
    except Exception:
        return None
    if mask.size != source.size:
        mask = mask.resize(source.size, Image.NEAREST)
    tint = Image.new("RGBA", source.size, (255, 76, 76, 0))
    alpha_mask = mask.point(lambda px: min(255, int(px * alpha / 255)))
    tint.putalpha(alpha_mask)
    return Image.alpha_composite(source, tint)


def show_image(label: str, path_value: Any, caption: str | None = None) -> None:
    st.markdown(f"**{label}**")
    if path_value is None:
        st.caption("missing")
        return
    text = str(path_value).strip()
    if not text:
        st.caption("missing")
        return
    path = Path(text)
    if path.exists() and path.is_file():
        st.image(str(path), use_container_width=True)
        if caption:
            st.caption(caption)
    else:
        st.caption("missing")


def show_overlay(label: str, source_value: Any, mask_value: Any) -> None:
    st.markdown(f"**{label}**")
    if source_value is None or mask_value is None or not str(source_value).strip() or not str(mask_value).strip():
        st.caption("missing")
        return
    overlay = build_mask_overlay(source_value, mask_value)
    if overlay is None:
        st.caption("missing")
        return
    st.image(overlay, use_container_width=True)


def inventory_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    data = []
    for row in rows:
        data.append(
            {
                "image": row.get("relative_path"),
                "status": row.get("status") or "ok",
                "reason": row.get("status_reason") or "",
                "copies": row.get("file_count"),
                "family_id": row.get("family_id") or "-",
                "applied": row.get("applied"),
                "coverage_gain": row.get("coverage_gain"),
                "raw_mask": row.get("raw_mask_coverage"),
                "ai_mask": row.get("refined_mask_coverage"),
                "instances": row.get("instance_count"),
                "step_x": row.get("step_x"),
                "step_y": row.get("step_y"),
                "detector_in": row.get("detector_input_best"),
            }
        )
    return pd.DataFrame(data)


def families_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    data = []
    for row in rows:
        data.append(
            {
                "family_id": row.get("family_id"),
                "count": row.get("count"),
                "applied_count": row.get("applied_count"),
                "mean_similarity": row.get("mean_similarity"),
                "coverage_gain": row.get("mean_coverage_gain"),
                "angle_deg": row.get("mean_angle_deg"),
                "step_x": row.get("mean_step_x"),
                "step_y": row.get("mean_step_y"),
            }
        )
    return pd.DataFrame(data)


def run_results_frame(rows: list[dict[str, Any]]) -> pd.DataFrame:
    data = []
    for row in rows:
        quality = row.get("quality") or {}
        detector = row.get("detector_output") or {}
        data.append(
            {
                "image": row.get("image"),
                "status": row.get("status"),
                "reason": row.get("status_reason") or row.get("error") or row.get("reject_reason") or "",
                "preset": row.get("preset_final"),
                "score": quality.get("score"),
                "mask_coverage": quality.get("mask_coverage"),
                "detector_out": detector.get("best_conf"),
                "time_total_sec": row.get("time_total_sec"),
                "stage_summary": row.get("stage_summary"),
            }
        )
    return pd.DataFrame(data)


workspace_default = st.session_state.get("workspace_path", str(ROOT))
config_default = st.session_state.get("config_path", str(ROOT / "config" / "explorer.yaml"))

st.title("wmRemove Project Workspace")
st.caption("Project root must contain an `images/` directory. All project metadata stays in `.wmremove/` and exports omit the gallery.")

init_status_state()
status_bar_placeholder = st.empty()
status_progress_placeholder = st.empty()
status_history_placeholder = st.empty()
render_status_panel()

with st.sidebar:
    st.header("Project")
    workspace_input = st.text_input("Workspace directory", workspace_default)
    config_input = st.text_input("Config YAML", config_default)
    output_input = st.text_input("Output directory", str(resolve_path(workspace_input) / "output"))
    export_input = st.text_input(
        "Export zip",
        str(resolve_path(workspace_input) / ".wmremove" / "exports" / "project_export.zip"),
    )
    create_clicked = st.button("Create / Open Project", use_container_width=True)
    index_clicked = st.button("Index Images", use_container_width=True)
    masks_clicked = st.button("Calculate Masks", use_container_width=True)
    export_clicked = st.button("Export Project", use_container_width=True)

workspace_path = resolve_path(workspace_input)
config_path = resolve_path(config_input)
output_path = resolve_path(output_input)
export_path = resolve_path(export_input)
paths = project_paths(workspace_path)
st.session_state["workspace_path"] = str(workspace_path)
st.session_state["config_path"] = str(config_path)

feedback = st.empty()

if create_clicked:
    try:
        set_status(
            state="running",
            phase="project",
            message="Opening project workspace",
            image=str(workspace_path),
            current=0,
            total=1,
            progress=0.05,
        )
        ensure_project(workspace_path, config_path=config_path)
        set_status(
            state="complete",
            phase="project",
            message="Project opened",
            image=str(workspace_path),
            current=1,
            total=1,
            progress=1.0,
            note="workspace_ready",
        )
        feedback.success(f"Project opened: {workspace_path}")
    except Exception as exc:
        set_status(
            state="error",
            phase="project",
            message="Project open failed",
            image=str(workspace_path),
            progress=0.0,
            note=str(exc),
        )
        feedback.error(str(exc))

if index_clicked:
    def on_index(event: dict[str, Any]) -> None:
        total = max(int(event.get("total") or 1), 1)
        current = int(event.get("current") or 0)
        set_status(
            state="running",
            phase="index",
            message="Indexing gallery",
            image=str(event.get("image") or paths.images_dir),
            current=current,
            total=total,
            note="hashing",
        )

    try:
        set_status(
            state="running",
            phase="index",
            message="Scanning images directory",
            image=str(paths.images_dir),
            current=0,
            total=1,
            progress=0.0,
        )
        summary = index_project_images(workspace_path, config_path=config_path, progress=on_index)
        set_status(
            state="complete",
            phase="index",
            message=f"Index complete: {summary['file_count']} files",
            image=str(paths.images_dir),
            current=summary["file_count"],
            total=max(summary["file_count"], 1),
            progress=1.0,
            note=f"unique={summary['unique_images']}",
        )
        feedback.success(f"Indexed {summary['file_count']} files ({summary['unique_images']} unique hashes)")
    except Exception as exc:
        set_status(
            state="error",
            phase="index",
            message="Indexing failed",
            image=str(paths.images_dir),
            progress=0.0,
            note=str(exc),
        )
        feedback.error(str(exc))

if masks_clicked:
    def on_masks(event: dict[str, Any]) -> None:
        total = max(int(event.get("total") or 1), 1)
        current = int(event.get("current") or 0)
        set_status(
            state="running",
            phase="masks",
            message="Calculating masks and pattern groups",
            image=str(event.get("image") or ""),
            current=current,
            total=total,
            note="routing",
        )

    try:
        set_status(
            state="running",
            phase="masks",
            message="Starting mask calculation",
            image=str(paths.images_dir),
            current=0,
            total=1,
            progress=0.0,
        )
        summary = calculate_project_masks(workspace_path, config_path=config_path, progress=on_masks)
        set_status(
            state="complete",
            phase="masks",
            message=f"Mask calculation complete: {summary['images']} images",
            image=str(paths.inventory_dir),
            current=summary["images"],
            total=max(summary["images"], 1),
            progress=1.0,
            note=f"families={summary['family_count']}",
        )
        feedback.success(f"Calculated masks for {summary['images']} unique images")
    except Exception as exc:
        set_status(
            state="error",
            phase="masks",
            message="Mask calculation failed",
            image=str(paths.inventory_dir),
            progress=0.0,
            note=str(exc),
        )
        feedback.error(str(exc))

if export_clicked:
    try:
        set_status(
            state="running",
            phase="export",
            message="Exporting project package",
            image=str(export_path),
            current=0,
            total=1,
            progress=0.2,
        )
        exported = export_project(workspace_path, export_path)
        set_status(
            state="complete",
            phase="export",
            message="Project export complete",
            image=str(exported["zip_path"]),
            current=1,
            total=1,
            progress=1.0,
            note=f"files={exported['file_count']}",
        )
        feedback.success(f"Export written to {exported['zip_path']}")
    except Exception as exc:
        set_status(
            state="error",
            phase="export",
            message="Project export failed",
            image=str(export_path),
            progress=0.0,
            note=str(exc),
        )
        feedback.error(str(exc))

load_issues: list[LoadIssue] = []
snapshot = build_project_snapshot(workspace_path, issues=load_issues)
unique_images = snapshot.unique_images
inventory_rows = snapshot.inventory_records
family_rows = snapshot.families
library_manifest = load_repeat_family_library(workspace_path, issues=load_issues)

index_summary = snapshot.index_summary
mask_summary = snapshot.mask_summary
runs = snapshot.runs

overview_cols = st.columns(4)
overview_cols[0].metric("Indexed Files", index_summary.get("file_count", 0))
overview_cols[1].metric("Unique Images", index_summary.get("unique_images", 0))
overview_cols[2].metric("Mask Groups", mask_summary.get("family_count", 0))
overview_cols[3].metric("Runs", len(runs))

if load_issues:
    st.warning(f"Loaded partial project data. Parsing issues: {len(load_issues)}")
    with st.expander("Load warnings", expanded=False):
        for line in format_load_issues(load_issues, limit=16):
            st.code(line)

tab_project, tab_masks, tab_clean, tab_runs = st.tabs(["Project", "Mask Review", "Batch Clean", "Runs"])

with tab_project:
    st.subheader("Project Status")
    st.write(f"Workspace: `{workspace_path}`")
    st.write(f"Images dir: `{paths.images_dir}`")
    st.write(f"Project dir: `{paths.project_dir}`")
    if not paths.images_dir.exists():
        st.warning("Create an `images/` folder inside the workspace and put the gallery there.")
    elif not index_summary:
        st.info("Start with `Index Images` in the sidebar.")
    else:
        status_cols = st.columns(3)
        status_cols[0].metric("Files", index_summary.get("file_count", 0))
        status_cols[1].metric("Unique hashes", index_summary.get("unique_images", 0))
        status_cols[2].metric("Duplicates", index_summary.get("duplicate_files", 0))
        if unique_images:
            frame = pd.DataFrame(
                [
                    {
                        "image": row["canonical_relative_path"],
                        "copies": row["file_count"],
                        "size": f"{row['width']}x{row['height']}",
                        "hash": row["image_id"][:16],
                    }
                    for row in unique_images
                ]
            )
            st.dataframe(frame, use_container_width=True, hide_index=True)

with tab_masks:
    st.subheader("Mask Groups")
    if not inventory_rows:
        st.info("Run `Calculate Masks` to unlock review and batch cleaning.")
    else:
        info_cols = st.columns(5)
        info_cols[0].metric("Processed images", mask_summary.get("images", len(inventory_rows)))
        info_cols[1].metric("Unsupported", mask_summary.get("unsupported_count", 0))
        info_cols[2].metric("Repeat applied", mask_summary.get("applied", 0))
        info_cols[3].metric("Families", mask_summary.get("family_count", 0))
        info_cols[4].metric("Detector", "ready" if mask_summary.get("detector_available") else "offline")

        if family_rows:
            st.dataframe(families_frame(family_rows), use_container_width=True, hide_index=True)
        else:
            st.caption("No repeat families were extracted. Inventory is still available below.")

        inventory_df = inventory_frame(inventory_rows)
        st.dataframe(inventory_df, use_container_width=True, hide_index=True)

        family_options = ["all"] + [row["family_id"] for row in family_rows]
        selected_family = st.selectbox("Preview family", family_options, index=0)
        if selected_family == "all":
            family_members = inventory_rows[:6]
            family_meta = None
        else:
            family_members = [row for row in inventory_rows if row.get("family_id") == selected_family]
            family_meta = next((row for row in library_manifest.get("families") or [] if row.get("family_id") == selected_family), None)

        if family_meta:
            family_cols = st.columns([1, 3])
            with family_cols[0]:
                show_image("Prototype", family_meta.get("prototype_mask_path"))
            with family_cols[1]:
                st.write(f"Family: `{selected_family}`")
                st.write(f"Sample images: {', '.join(family_meta.get('sample_images') or [])}")

        for member in family_members[:6]:
            st.markdown(f"### {member.get('relative_path')}")
            cols = st.columns(4)
            with cols[0]:
                show_image("Source", member.get("image_path"))
            with cols[1]:
                show_overlay("AI mask overlay", member.get("image_path"), member.get("ai_mask_path"))
            with cols[2]:
                show_image("Repeat template", member.get("repeat_template_path"))
            with cols[3]:
                show_image("Repeat render", member.get("repeat_render_path"))

with tab_clean:
    st.subheader("Batch Clean")
    if not inventory_rows:
        st.warning("Mask calculation has to finish before cleaning can run.")
    else:
        selection_mode = st.radio("Selection", ["All indexed images", "Random percent"], horizontal=True)
        percent = 100
        seed = 1337
        if selection_mode == "Random percent":
            percent = st.slider("Random sample percent", 1, 100, 25)
            seed = int(st.number_input("Sample seed", min_value=0, value=1337))
        selected_ids = choose_image_ids(
            workspace_path,
            mode="all" if selection_mode == "All indexed images" else "random",
            percent=float(percent),
            seed=seed,
        )
        st.caption(f"Selected unique hashes: {len(selected_ids)}")

        with st.expander("Execution settings", expanded=False):
            call_budget = int(st.number_input("Total call budget (0 = auto)", min_value=0, value=0))
            quality_threshold = float(st.number_input("Quality fail threshold", min_value=0.0, max_value=1.0, value=0.72, step=0.01))
            detector_threshold = float(st.number_input("Detector fail threshold", min_value=0.0, max_value=1.0, value=0.18, step=0.01))

        if st.button("Run Cleaning", type="primary", use_container_width=True):
            def on_run(event: dict[str, Any]) -> None:
                total = max(int(event.get("total") or 1), 1)
                current = int(event.get("current") or 0)
                phase = str(event.get("phase") or "run")
                image = str(event.get("image") or "")
                note_parts = []
                if event.get("status"):
                    note_parts.append(str(event["status"]))
                if event.get("calls") is not None:
                    note_parts.append(f"calls={event['calls']}")
                set_status(
                    state="running",
                    phase=phase,
                    message=f"{phase}: {image or 'working'}",
                    image=image or str(output_path),
                    current=current,
                    total=total,
                    score=event.get("score"),
                    detector=event.get("detector"),
                    calls=event.get("calls"),
                    note=", ".join(note_parts),
                )

            try:
                set_status(
                    state="running",
                    phase="selection",
                    message="Preparing batch selection",
                    image=str(output_path),
                    current=0,
                    total=max(len(selected_ids), 1),
                    progress=0.0,
                    calls=call_budget if call_budget > 0 else "auto",
                    note=f"selected={len(selected_ids)}",
                )
                result = run_project_batch(
                    workspace_path,
                    config_path,
                    selected_ids,
                    output_path,
                    call_budget=call_budget,
                    quality_fail_threshold=quality_threshold,
                    detector_fail_threshold=detector_threshold,
                    progress=on_run,
                )
                summary = result["summary"]
                runs = list_project_runs(workspace_path)
                set_status(
                    state="complete",
                    phase="batch",
                    message=f"Batch complete: run {summary.get('run_id')}",
                    image=str(summary.get("published_output_dir") or output_path),
                    current=summary.get("published_files", 0),
                    total=max(summary.get("published_files", 0), 1),
                    progress=1.0,
                    score=summary.get("quality_avg_score"),
                    note=f"published={summary.get('published_files', 0)}",
                )
                st.success(
                    f"Run {summary.get('run_id')} complete. "
                    f"Published {summary.get('published_files', 0)} files to {summary.get('published_output_dir')}"
                )
                st.json(
                    {
                        "run_dir": result.get("run_dir"),
                        "report_html": summary.get("reports", {}).get("html"),
                        "report_csv": summary.get("reports", {}).get("csv"),
                        "published_output_dir": summary.get("published_output_dir"),
                    }
                )
            except Exception as exc:
                set_status(
                    state="error",
                    phase="batch",
                    message="Batch execution failed",
                    image=str(output_path),
                    progress=0.0,
                    note=str(exc),
                )
                st.error(str(exc))

with tab_runs:
    st.subheader("Run Explorer")
    if not runs:
        st.info("No project runs yet.")
    else:
        run_names = [run["name"] for run in runs]
        selected_name = st.selectbox("Run", run_names, index=0)
        selected_run = next(run for run in runs if run["name"] == selected_name)
        run_dir = Path(selected_run["run_dir"])
        summary = selected_run["summary"]
        run_cols = st.columns(5)
        run_cols[0].metric("Success", summary.get("success_count", 0))
        run_cols[1].metric("Unsupported", summary.get("unsupported_count", 0))
        run_cols[2].metric("Rejected", summary.get("rejected_count", 0))
        run_cols[3].metric("Avg score", format_float(summary.get("quality_avg_score")))
        run_cols[4].metric("Published files", summary.get("published_files", 0))
        st.write(f"Run dir: `{run_dir}`")
        st.write(f"Published output: `{summary.get('published_output_dir', '-')}`")

        run_issues: list[LoadIssue] = []
        run_rows = read_jsonl(run_dir / "results.jsonl", issues=run_issues, source=f"run results {selected_name}")
        if run_issues:
            st.warning(f"Run data has parsing issues: {len(run_issues)}")
            with st.expander("Run parsing warnings", expanded=False):
                for line in format_load_issues(run_issues, limit=12):
                    st.code(line)
        if run_rows:
            st.dataframe(run_results_frame(run_rows), use_container_width=True, hide_index=True)
            preview_name = st.selectbox("Preview image", [row["image"] for row in run_rows], index=0)
            preview = next(row for row in run_rows if row["image"] == preview_name)
            preview_cols = st.columns(4)
            with preview_cols[0]:
                show_image("Source", preview.get("source_path"))
            with preview_cols[1]:
                show_image("Prepared", preview.get("prepared_source"))
            with preview_cols[2]:
                show_overlay("Mask overlay", preview.get("source_path"), preview.get("ai_mask"))
            with preview_cols[3]:
                show_image("Final output", preview.get("output"))


