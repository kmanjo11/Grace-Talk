import os
from pathlib import Path
import streamlit as st
import pandas as pd
from src.utils.pdf_parser import parse_pdf_text
try:
    from xerparser.reader import Reader  # preferred
except Exception:
    try:
        # some distributions expose Reader at top-level or different module
        from pyp6xer import Reader  # fallback
    except Exception:
        Reader = None

UPLOAD_DIR = Path("./workspace/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

REVIEW_TYPES = {
    'Single Schedule Review': 'single_schedule',
    'Schedule Comparison': 'schedule_comparison',
    'Time Impact Analysis (TIA) Review': 'tia_review',
    'Delay Analysis Review': 'delay_analysis'
}


def _save_uploaded_file(uploaded, suffix_filter=None) -> str:
    if not uploaded:
        return ""
    name = uploaded.name
    if suffix_filter and not name.lower().endswith(tuple(suffix_filter)):
        return ""
    dest = UPLOAD_DIR / name
    with open(dest, 'wb') as f:
        f.write(uploaded.getbuffer())
    return str(dest)


def _analyze_lags(predecessors) -> dict:
    rels_with_lags = 0
    total = 0
    dist = {}
    for rel in predecessors:
        total += 1
        # Support multiple attribute names across libraries
        lag = 0
        for cand in ('lag_hr_cnt', 'lag', 'lag_hours', 'lag_hr'):
            try:
                v = getattr(rel, cand)
                if v is not None:
                    lag = v
                    break
            except Exception:
                continue
        lag = lag or 0
        if lag != 0:
            rels_with_lags += 1
            lag_days = lag / 8.0
            dist[lag_days] = dist.get(lag_days, 0) + 1
    pct = (rels_with_lags / total * 100.0) if total else 0.0
    return {
        'total_relationships': total,
        'with_lags': rels_with_lags,
        'percent_with_lags': pct,
        'distribution_days': dict(sorted(dist.items()))
    }


def _generate_instructions(project_info, counts, files, review_type) -> str:
    return f"""
🤖 AI ASSISTANT INSTRUCTIONS FOR P6 SCHEDULE REVIEW
================================================

PROJECT CONTEXT:
• Project: {project_info.get('name','Unknown')}
• Review Type: {review_type.replace('_', ' ').title()}
• Activities: {counts['activity_count']:,}
• Relationships: {counts['relationship_count']:,}

ANALYSIS FRAMEWORK:
1. Use PyP6XER (xerparser.Reader) for all schedule data parsing.
2. Treat specifications as the authoritative reference ("law of the land").
3. Reference spec locations using: "Specification [SECTION] [SUBSECTION]".
4. Flag narrative statements that contradict specifications.
5. Provide evidence-based analysis with activity IDs and relationship details.

AVAILABLE INPUTS:
• XER File: {Path(files.get('xer_file') or '').name if files.get('xer_file') else 'None'}
• Narrative: {Path(files.get('narrative_file') or '').name if files.get('narrative_file') else 'None'}
• Specifications: {Path(files.get('spec_file') or '').name if files.get('spec_file') else 'None'}

KEY ANALYSIS AREAS:
• Schedule logic and relationships
• Float analysis and critical path
• Specification compliance
• Responsibility analysis (contractor vs owner)
• Non-compensable delays
• Resource and crew management

When proposing fixes or findings, be concise, cite specific activities, and reference specs when applicable.
""".strip()


def p6_panel():
    st.subheader("P6 Schedule Review Setup")
    st.caption("Upload your schedule artifacts and generate an AI analysis context. Files are saved under ./workspace/uploads/")

    col1, col2, col3 = st.columns(3)
    with col1:
        xer_u = st.file_uploader("XER file", type=["xer"], key="p6_xer")
    with col2:
        narrative_u = st.file_uploader("Narrative (PDF)", type=["pdf"], key="p6_narr")
    with col3:
        spec_u = st.file_uploader("Specification (PDF/Doc)", type=["pdf","doc","docx"], key="p6_spec")

    review_label = st.selectbox("Review Type", list(REVIEW_TYPES.keys()), index=0)
    run = st.button("Generate P6 Analysis Context", type="primary")

    # Optional: additional supporting files (saved in workspace/uploads for later reference)
    extra_files = st.file_uploader("Additional supporting files (optional)", type=["pdf","doc","docx","xls","xlsx","csv","txt"], accept_multiple_files=True, key="p6_extra")
    if extra_files:
        for f in extra_files:
            _ = _save_uploaded_file(f)

    if run:
        xer_path = _save_uploaded_file(xer_u, suffix_filter=[".xer"]) if xer_u else ""
        narrative_path = _save_uploaded_file(narrative_u) if narrative_u else ""
        spec_path = _save_uploaded_file(spec_u) if spec_u else ""

        if not xer_path:
            st.error("Please upload an XER file.")
            return

        try:
            if Reader is None:
                raise RuntimeError("No compatible XER parser found. Please ensure 'xerparser' or 'pyp6xer' is installed.")
            reader = Reader(xer_path)
            # Robust project access
            projects = []
            for cand in ('projects', 'project_list', 'project'):
                if hasattr(reader, cand):
                    try:
                        val = getattr(reader, cand)
                        projects = list(val) if not isinstance(val, list) else val
                        break
                    except Exception:
                        continue
            project = projects[0] if projects else None
            project_info = {
                'id': getattr(project, 'id', 'Unknown') if project else 'Unknown',
                'name': getattr(project, 'proj_short_name', getattr(project, 'name', 'Unknown')) if project else 'Unknown',
                'start_date': getattr(project, 'plan_start_date', 'Unknown') if project else 'Unknown',
                'finish_date': getattr(project, 'plan_end_date', 'Unknown') if project else 'Unknown',
            }

            def _fetch_list(obj, candidates):
                for cand in candidates:
                    if hasattr(obj, cand):
                        try:
                            val = getattr(obj, cand)
                            return list(val) if not isinstance(val, list) else val
                        except Exception:
                            continue
                return []

            def _detect_used_attr(obj, candidates):
                for cand in candidates:
                    if hasattr(obj, cand):
                        try:
                            getattr(obj, cand)
                            return cand
                        except Exception:
                            continue
                return ''

            act_cands = ('tasks', 'activities', 'activity')
            rel_cands = ('predecessors', 'relationships', 'rels', 'relations')
            res_cands = ('resources', 'resource_assignments', 'resource')
            wbs_cands = ('wbss', 'wbs')

            activities = _fetch_list(reader, act_cands)
            predecessors = _fetch_list(reader, rel_cands)
            resources = _fetch_list(reader, res_cands)
            wbss = _fetch_list(reader, wbs_cands)
            counts = {
                'activity_count': len(activities),
                'relationship_count': len(predecessors),
                'resource_count': len(resources),
                'wbs_count': len(wbss)
            }

            lag_stats = _analyze_lags(predecessors)

            files = {
                'xer_file': xer_path,
                'narrative_file': narrative_path,
                'spec_file': spec_path
            }

            # Parse PDFs (Narrative/Spec) using LlamaParse (or fallback) and add compact excerpts
            doc_excerpts = []
            if narrative_path:
                text, engine = parse_pdf_text(narrative_path, max_chars=50_000)
                if text:
                    snippet = text[:2000]
                    doc_excerpts.append(f"Narrative ({engine}):\n{snippet}\n...")
            if spec_path:
                text, engine = parse_pdf_text(spec_path, max_chars=50_000)
                if text:
                    snippet = text[:2000]
                    doc_excerpts.append(f"Specification ({engine}):\n{snippet}\n...")

            instructions = _generate_instructions(project_info, counts, files, REVIEW_TYPES[review_label])
            if doc_excerpts:
                instructions = (
                    instructions
                    + "\n\nDOCUMENT EXCERPTS (for context)\n-------------------------------\n"
                    + "\n\n".join(doc_excerpts)
                )

            # Save context to workspace
            ctx_path = Path("./workspace/schedule_review_context.txt")
            ctx_path.write_text(instructions, encoding="utf-8")

            # Persist in session_state for hidden prompt augmentation if enabled
            st.session_state['p6_context'] = instructions
            st.session_state['p6_source_xer'] = xer_path

            # Persist dataframes for export
            def _to_df(objs):
                rows = []
                for o in objs:
                    row = {}
                    for attr in dir(o):
                        if attr.startswith('_'):
                            continue
                        try:
                            v = getattr(o, attr)
                        except Exception:
                            continue
                        if callable(v):
                            continue
                        if isinstance(v, (str, int, float, bool)) or v is None:
                            row[attr] = v
                    if row:
                        rows.append(row)
                return pd.DataFrame(rows)

            st.session_state['p6_dfs'] = {
                'activities': _to_df(activities),
                'relationships': _to_df(predecessors),
                'resources': _to_df(resources),
                'wbs': _to_df(wbss),
            }

            st.success("P6 analysis context generated. It will be used silently when enabled in the sidebar.")

            with st.expander("Summary", expanded=True):
                st.markdown(f"**Project**: {project_info['name']}")
                st.markdown(f"**Activities**: {counts['activity_count']:,}")
                st.markdown(f"**Relationships**: {counts['relationship_count']:,}")
                st.markdown(f"**Resources**: {counts['resource_count']:,}")
                st.markdown(f"**WBS Elements**: {counts['wbs_count']:,}")
                st.markdown("**Lag Analysis**:")
                st.markdown(f"- with lags: {lag_stats['with_lags']} / {lag_stats['total_relationships']} ({lag_stats['percent_with_lags']:.1f}%)")
                if lag_stats['distribution_days']:
                    for d, c in lag_stats['distribution_days'].items():
                        st.markdown(f"  - {d:+.1f} days: {c}")

            with st.expander("Debug (Reader attributes)", expanded=False):
                st.caption("Detected attribute names on your Reader; this helps ensure compatibility across PyP6XER variants.")
                st.write({
                    'projects_attr_present': [c for c in ('projects','project_list','project') if hasattr(reader,c)],
                    'activities_attr_present': [c for c in act_cands if hasattr(reader,c)],
                    'relationships_attr_present': [c for c in rel_cands if hasattr(reader,c)],
                    'resources_attr_present': [c for c in res_cands if hasattr(reader,c)],
                    'wbs_attr_present': [c for c in wbs_cands if hasattr(reader,c)],
                })

            st.download_button("Download context", data=instructions, file_name="schedule_review_context.txt")
        except Exception as e:
            st.error(f"Failed to parse XER: {e}")

    # Interactive assistant mode (no external scripts)
    st.divider()
    enabled = st.toggle("Enable P6 Interactive Assistant (use context silently in chat)", value=True)
    st.session_state['p6_interactive'] = enabled

    # Export panel
    st.subheader("Exports")
    st.caption("Download parsed schedule tables as CSV/Excel. XER export is attempted if a compatible writer is available.")
    dfs = st.session_state.get('p6_dfs', {})
    if dfs:
        colA, colB, colC, colD = st.columns(4)
        with colA:
            if 'activities' in dfs and not dfs['activities'].empty:
                csv = dfs['activities'].to_csv(index=False).encode('utf-8')
                st.download_button("Activities CSV", data=csv, file_name="activities.csv")
        with colB:
            if 'relationships' in dfs and not dfs['relationships'].empty:
                csv = dfs['relationships'].to_csv(index=False).encode('utf-8')
                st.download_button("Relationships CSV", data=csv, file_name="relationships.csv")
        with colC:
            if 'resources' in dfs and not dfs['resources'].empty:
                csv = dfs['resources'].to_csv(index=False).encode('utf-8')
                st.download_button("Resources CSV", data=csv, file_name="resources.csv")
        with colD:
            if 'wbs' in dfs and not dfs['wbs'].empty:
                csv = dfs['wbs'].to_csv(index=False).encode('utf-8')
                st.download_button("WBS CSV", data=csv, file_name="wbs.csv")

        # Excel export (single workbook with multiple sheets)
        if st.button("Download Excel Workbook"):
            try:
                from io import BytesIO
                bio = BytesIO()
                with pd.ExcelWriter(bio, engine='xlsxwriter') as writer:
                    for name, df in dfs.items():
                        if not df.empty:
                            df.to_excel(writer, sheet_name=name[:31], index=False)
                bio.seek(0)
                st.download_button("Download Excel", data=bio.getvalue(), file_name="schedule_tables.xlsx")
            except Exception as e:
                st.warning(f"Excel export failed: {e}")

        # Experimental XER export
        st.markdown("---")
        st.caption("XER export (experimental)")
        xer_writer = None
        try:
            from xerparser.writer import Writer as _XERWriter
            xer_writer = _XERWriter
        except Exception:
            try:
                from pyp6xer import Writer as _XERWriter
                xer_writer = _XERWriter
            except Exception:
                xer_writer = None

        if xer_writer is None:
            st.info("A compatible XER writer was not found. CSV/Excel exports are available.")
        else:
            out_name = st.text_input("Output XER filename", value="exported_schedule.xer")
            if st.button("Export to XER (experimental)"):
                try:
                    # Best-effort: attempt to initialize the writer and write out
                    # Note: exact API may vary; wrap in try/except to avoid breaking UI
                    source_path = st.session_state.get('p6_source_xer')
                    if not source_path:
                        raise RuntimeError("No parsed XER source available in session.")
                    out_path = str(Path('./workspace') / out_name)
                    # Common patterns seen in writer APIs (adjust as available):
                    try:
                        writer_obj = xer_writer()
                        writer_obj.write(out_path)
                        st.success(f"Exported XER to {out_path}")
                    except Exception:
                        # Alternate API: writer takes source path and destination
                        try:
                            writer_obj = xer_writer(source_path)
                            writer_obj.write(out_path)
                            st.success(f"Exported XER to {out_path}")
                        except Exception as inner:
                            raise inner
                except Exception as e:
                    st.error(f"XER export failed or is unsupported in this environment: {e}")
                    st.info("Please use CSV/Excel exports as a reliable fallback, or share your writer API details to enable full XER writing.")
    else:
        st.caption("No parsed schedule found yet. Generate P6 Analysis Context first.")
