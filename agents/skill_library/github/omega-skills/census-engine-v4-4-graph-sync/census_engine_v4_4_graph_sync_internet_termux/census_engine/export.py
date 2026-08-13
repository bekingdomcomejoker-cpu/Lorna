import json, html
from .db import connect

def graph_data(db_path, run_id=None):
    con = connect(db_path)
    if run_id:
        nodes = [dict(r) for r in con.execute("SELECT * FROM graph_nodes WHERE run_id=?", (run_id,))]
        edges = [dict(r) for r in con.execute("SELECT * FROM graph_edges WHERE run_id=?", (run_id,))]
    else:
        nodes = [dict(r) for r in con.execute("SELECT * FROM graph_nodes")]
        edges = [dict(r) for r in con.execute("SELECT * FROM graph_edges")]
    con.close()
    for n in nodes:
        try: n["data"] = json.loads(n.pop("data_json") or "{}")
        except Exception: n["data"] = {}
    for e in edges:
        try: e["data"] = json.loads(e.pop("data_json") or "{}")
        except Exception: e["data"] = {}
    return {"nodes": nodes, "edges": edges}

def export_json(db_path, out_path, run_id=None):
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(graph_data(db_path, run_id), f, indent=2, ensure_ascii=False)
    return out_path

def export_graphml(db_path, out_path, run_id=None):
    data = graph_data(db_path, run_id)
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<graphml xmlns="http://graphml.graphdrawing.org/xmlns">',
             '<key id="label" for="node" attr.name="label" attr.type="string"/>',
             '<key id="type" for="node" attr.name="type" attr.type="string"/>',
             '<key id="etype" for="edge" attr.name="edge_type" attr.type="string"/>',
             '<graph id="CensusEngine" edgedefault="directed">']
    for n in data["nodes"]:
        nid = html.escape(n["node_id"])
        label = html.escape(n.get("label") or "")
        ntype = html.escape(n.get("node_type") or "")
        lines.append(f'<node id="{nid}"><data key="label">{label}</data><data key="type">{ntype}</data></node>')
    for e in data["edges"]:
        eid = html.escape(e["edge_id"])
        src = html.escape(e["source_node"])
        tgt = html.escape(e["target_node"])
        et = html.escape(e["edge_type"])
        lines.append(f'<edge id="{eid}" source="{src}" target="{tgt}"><data key="etype">{et}</data></edge>')
    lines += ['</graph>', '</graphml>']
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_path
