import streamlit as st
import json
import uuid
from streamlit_agraph import agraph, Node, Edge, Config

st.set_page_config(page_title="Procesflow Digital Tvilling", layout="wide")
st.title("🔁 Digital Tvilling af Procesflow")

# --- Initialiser session state ---
if "processes" not in st.session_state:
    st.session_state["processes"] = {}
if "edges" not in st.session_state:
    st.session_state["edges"] = []

for key in ["x", "y", "P", "f", "w"]:
    if f"new_materials_{key}" not in st.session_state:
        st.session_state[f"new_materials_{key}"] = []

# --- Funktion til at beregne detaljescore ---
def calculate_detail_score(inputs):
    score = 1.0
    if not inputs.get("x") or not inputs.get("y"):
        score -= 0.3
    if not inputs.get("P"):
        score -= 0.2
    if not inputs.get("f") or not inputs.get("w"):
        score -= 0.3
    return max(0.0, min(score, 1.0))

# --- Materiale inputsektion ---
def material_editor(section):
    st.markdown(f"#### {section} (format: Navn: mængde enhed)")
    col1, col2 = st.columns([4,1])
    with col1:
        entry = st.text_input(f"Tilføj {section}", key=f"input_{section}")
    with col2:
        if st.button("➕", key=f"add_{section}") and entry:
            st.session_state[f"new_materials_{section}"].append(entry)

    for i, item in enumerate(st.session_state[f"new_materials_{section}"]):
        cols = st.columns([8,1])
        with cols[0]:
            st.markdown(f"- {item}")
        with cols[1]:
            if cols[1].button("❌", key=f"remove_{section}_{i}"):
                st.session_state[f"new_materials_{section}"].pop(i)
                st.rerun()

def get_material_string(section):
    return "\n".join(st.session_state[f"new_materials_{section}"])

# --- Indlæs/gem JSON ---
with st.sidebar:
    st.subheader("📂 Gem/Indlæs")
    uploaded_file = st.file_uploader("Indlæs værdikæde JSON", type=["json"])
    if uploaded_file:
        data = json.load(uploaded_file)
        st.session_state.processes = data.get("processes", {})
        st.session_state.edges = data.get("edges", [])
        st.success("Værdikæde indlæst")

    if st.button("💾 Gem nuværende værdikæde"):
        export = {
            "processes": st.session_state.processes,
            "edges": st.session_state.edges
        }
        st.download_button(
            label="Download som JSON",
            data=json.dumps(export, indent=2),
            file_name="vaerdikaede.json",
            mime="application/json"
        )

# --- Tilføj ny proces ---
st.subheader("➕ Tilføj ny proces")
name = st.text_input("Navn på proces")
material_editor("x")
material_editor("y")
material_editor("P")
material_editor("f")
material_editor("w")

if st.button("✅ Tilføj proces") and name:
    x = get_material_string("x")
    y = get_material_string("y")
    P = get_material_string("P")
    f = get_material_string("f")
    w = get_material_string("w")
    pid = str(uuid.uuid4())
    st.session_state.processes[pid] = {
        "name": name, "x": x, "y": y, "P": P,
        "f": f, "w": w,
        "D": calculate_detail_score({"x": x, "y": y, "P": P, "f": f, "w": w}),
        "subprocesses": [],
        "is_aggregated": False
    }
    for key in ["x", "y", "P", "f", "w"]:
        st.session_state[f"new_materials_{key}"] = []
    st.rerun()

# RESTEN AF KODEN FORBLIVER UÆNDRET ...



# --- Visualisering af procesflow ---
st.subheader("🧠 Vis procesflow")
nodes = []
edges = []
for pid, pdata in st.session_state.processes.items():
    d_color = "#2ecc71" if pdata['D'] > 0.7 else "#f1c40f" if pdata['D'] > 0.4 else "#e74c3c"
    label = f"{pdata['name']}\nD={pdata['D']:.2f}"
    if pdata.get("is_aggregated"):
        label = "[Agg] " + label
    nodes.append(Node(id=pid, label=label, shape="box", color=d_color))
    for spid in pdata.get("subprocesses", []):
        edges.append(Edge(source=pid, target=spid, label="subprocess"))
for edge in st.session_state.edges:
    edges.append(Edge(source=edge[0], target=edge[1]))

config = Config(width=1000, height=600, directed=True, physics=True)
ag_output = agraph(nodes=nodes, edges=edges, config=config)

# --- Forbind processer ---
st.subheader("🔗 Forbind processer")
all_keys = list(st.session_state.processes.keys())
name_map = {k: st.session_state.processes[k]['name'] for k in all_keys}
source = st.selectbox("Fra proces", options=all_keys, format_func=lambda k: name_map[k], key="connect_source")
target = st.selectbox("Til proces", options=[k for k in all_keys if k != source], format_func=lambda k: name_map[k], key="connect_target")

if st.button("Tilføj forbindelse"):
    if (source, target) not in st.session_state.edges:
        st.session_state.edges.append((source, target))
        st.rerun()

# --- Split en proces til flere ---
st.subheader("🔀 Split en proces til flere mål")
split_source = st.selectbox("Vælg kildeproces", options=all_keys, format_func=lambda k: name_map[k], key="split_source")
split_targets = st.multiselect("Vælg målprocesser", options=[k for k in all_keys if k != split_source], format_func=lambda k: name_map[k], key="split_targets")

if st.button("Tilføj split-forbindelser"):
    for target in split_targets:
        if (split_source, target) not in st.session_state.edges:
            st.session_state.edges.append((split_source, target))
    st.rerun()

# --- Flow-simulering ---
st.subheader("🔬 Flowanalyse (simuleret)")
flow_info = []
for edge in st.session_state.edges:
    src, tgt = edge
    src_f = st.session_state.processes[src].get("f", "")
    tgt_x = st.session_state.processes[tgt].get("x", "")
    match = src_f.strip().lower() == tgt_x.strip().lower()
    flow_info.append((src, tgt, match))
    if not match:
        st.error(f"Mismatch mellem output fra '{name_map[src]}' og input til '{name_map[tgt]}'")
    else:
        st.success(f"✔ Output fra '{name_map[src]}' passer med input til '{name_map[tgt]}'")

# --- Rediger eksisterende proces ---
st.subheader("✏️ Rediger eksisterende proces")
edit_pid = st.selectbox("Vælg proces til redigering", options=all_keys, format_func=lambda k: name_map[k], key="edit_select")
if edit_pid:
    pdata = st.session_state.processes[edit_pid]
    with st.form("edit_process_form"):
        name = st.text_input("Navn på proces", value=pdata["name"])
        x = st.text_area("Inputmaterialer (x)", value=pdata["x"])
        y = st.text_area("Ressourcer (y)", value=pdata["y"])
        P = st.text_area("Procesparametre (P)", value=pdata["P"])
        f = st.text_area("Outputprodukter (f)", value=pdata["f"])
        w = st.text_area("Spild/affald (w)", value=pdata["w"])
        is_aggregated = st.checkbox("📦 Marker som aggregeret proces", value=pdata.get("is_aggregated", False))
        subprocesses = st.multiselect("Vælg underprocesser", options=[k for k in all_keys if k != edit_pid],
                                      default=pdata.get("subprocesses", []), format_func=lambda k: name_map[k])

        delete = st.checkbox("🗑️ Slet denne proces")
        submitted = st.form_submit_button("Gem ændringer")
        if submitted:
            if delete:
                st.session_state.processes.pop(edit_pid)
                st.session_state.edges = [e for e in st.session_state.edges if e[0] != edit_pid and e[1] != edit_pid]
                st.rerun()
            else:
                st.session_state.processes[edit_pid] = {
                    "name": name, "x": x, "y": y, "P": P,
                    "f": f, "w": w,
                    "D": calculate_detail_score({"x": x, "y": y, "P": P, "f": f, "w": w}),
                    "is_aggregated": is_aggregated,
                    "subprocesses": subprocesses
                }
                st.rerun()

# --- Liste over processer ---
st.sidebar.subheader("🔍 Alle processer")
for pid, pdata in st.session_state.processes.items():
    agg_text = " (Agg)" if pdata.get("is_aggregated") else ""
    st.sidebar.markdown(f"**{pdata['name']}{agg_text}**\n- D: {pdata['D']:.2f}")