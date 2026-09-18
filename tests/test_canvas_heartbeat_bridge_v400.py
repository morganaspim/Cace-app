from cace_studio.runtime.canvas_bridge import compile_canvas_heartbeat


def test_canvas_positions_and_tiling_do_not_change_heartbeat_semantic_graph_hash():
    base = {
        "nodes": [
            {"id": "a", "module_id": "m.a", "position": [0, 0], "params": {"__heartbeat": {"mode": "PERIODIC", "period_ticks": 2}}},
            {"id": "b", "module_id": "m.b", "position": [10, 20], "params": {}},
        ],
        "edges": [{"source_node": "a", "source_port": "x", "target_node": "b", "target_port": "y"}],
        "tiling_mode": "cartesian_square",
        "rotation_3d": {"x": 0, "y": 0, "z": 0},
    }
    _, first = compile_canvas_heartbeat(base, master_seed="s", hash_algorithm="sha256")
    changed_view = {
        **base,
        "nodes": [
            {**base["nodes"][0], "position": [999, -22]},
            {**base["nodes"][1], "position": [-100, 500]},
        ],
        "tiling_mode": "hexagonal_honeycomb",
        "rotation_3d": {"x": 30, "y": 80, "z": 10},
    }
    _, second = compile_canvas_heartbeat(changed_view, master_seed="s", hash_algorithm="sha256")
    assert first["graph_hash"] == second["graph_hash"]
    assert first["node_count"] == 2 and first["edge_count"] == 1
