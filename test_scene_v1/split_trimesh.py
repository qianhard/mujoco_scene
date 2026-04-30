# import trimesh
# import numpy as np
# import os
# import sys
#
#
# # ===================== 安全删除退化面（兼容旧版本） =====================
# def remove_degenerate_faces_safe(mesh):
#     if len(mesh.faces) == 0:
#         return mesh
#
#     v = mesh.vertices
#     f = mesh.faces
#
#     v0 = v[f[:, 0]]
#     v1 = v[f[:, 1]]
#     v2 = v[f[:, 2]]
#
#     area = np.linalg.norm(np.cross(v1 - v0, v2 - v0), axis=1)
#
#     mask = area > 1e-12
#     mesh.update_faces(mask)
#     mesh.remove_unreferenced_vertices()
#
#     return mesh
#
#
# # ===================== 挤出 =====================
# def extrude_mesh_manual(mesh, extrude_vector):
#     v_bottom = mesh.vertices.copy()
#     v_top = v_bottom + extrude_vector
#
#     f_bottom = mesh.faces.copy()
#     f_top = np.fliplr(f_bottom)
#
#     # ===== 边界检测（兼容所有版本） =====
#     edges = mesh.edges_unique
#     internal_edges = mesh.face_adjacency_edges
#
#     internal_set = set(map(tuple, np.sort(internal_edges, axis=1)))
#
#     boundary_edges = []
#     for e in edges:
#         if tuple(sorted(e)) not in internal_set:
#             boundary_edges.append(e)
#
#     boundary_edges = np.array(boundary_edges)
#
#     offset = len(v_bottom)
#     side_faces = []
#
#     for v0, v1 in boundary_edges:
#         side_faces.append([v0, v1, v0 + offset])
#         side_faces.append([v1, v1 + offset, v0 + offset])
#
#     side_faces = np.array(side_faces) if len(side_faces) > 0 else np.zeros((0, 3), dtype=np.int64)
#
#     all_vertices = np.vstack([v_bottom, v_top])
#     all_faces = np.vstack([f_bottom, f_top + offset, side_faces])
#
#     mesh_out = trimesh.Trimesh(vertices=all_vertices, faces=all_faces)
#
#     mesh_out = remove_degenerate_faces_safe(mesh_out)
#     mesh_out.remove_unreferenced_vertices()
#
#     return mesh_out
#
#
# # ===================== PCA厚度 =====================
# def compute_mesh_thickness_pca(mesh):
#     if len(mesh.vertices) < 3:
#         return 0, np.array([0, 0, 1])
#
#     cov = np.cov(mesh.vertices.T)
#     eigvals, eigvecs = np.linalg.eigh(cov)
#
#     idx = np.argmin(eigvals)
#     normal_dir = eigvecs[:, idx]
#
#     if np.linalg.norm(normal_dir) < 1e-8:
#         normal_dir = np.array([0, 0, 1])
#
#     proj = mesh.vertices @ normal_dir
#     thickness = proj.max() - proj.min()
#
#     return thickness, normal_dir
#
#
# def ensure_thickness(mesh, min_thickness=0.05):
#     if mesh.is_empty or len(mesh.vertices) < 3:
#         return mesh
#
#     thickness, normal_dir = compute_mesh_thickness_pca(mesh)
#
#     if thickness >= min_thickness:
#         return mesh
#
#     print(f"    → 当前厚度={thickness:.6f}，开始加厚")
#
#     extrude_vec = normal_dir * (min_thickness - thickness)
#
#     if np.linalg.norm(extrude_vec) < 1e-8:
#         extrude_vec = np.array([0, 0, min_thickness])
#
#     mesh_fixed = extrude_mesh_manual(mesh, extrude_vec)
#
#     return mesh_fixed
#
#
# # ===================== 距离判断 =====================
# def check_mesh_close(mesh1, mesh2, tol):
#     b1_min, b1_max = mesh1.bounds
#     b2_min, b2_max = mesh2.bounds
#
#     # 计算两个AABB之间的距离
#     dist = np.maximum(0, np.maximum(b1_min - b2_max, b2_min - b1_max))
#     dist = np.linalg.norm(dist)
#
#     return dist < tol
#
#
#
# # ===================== 聚类（关键升级） =====================
# def cluster_meshes(meshes, tol):
#     groups = []
#
#     for mesh in meshes:
#         assigned = False
#
#         for group in groups:
#             for g in group:
#                 if check_mesh_close(mesh, g, tol):
#                     group.append(mesh)
#                     assigned = True
#                     break
#             if assigned:
#                 break
#
#         if not assigned:
#             groups.append([mesh])
#
#     result = []
#     for g in groups:
#         combined = trimesh.util.concatenate(g)
#         combined.remove_unreferenced_vertices()
#         result.append(combined)
#
#     return result
#
#
# # ===================== 加载 + split =====================
# def load_all_original_meshes(loaded_model):
#     meshes = []
#
#     if isinstance(loaded_model, trimesh.Scene):
#         for geom in loaded_model.geometry.values():
#             if isinstance(geom, trimesh.Trimesh):
#                 meshes.append(geom)
#
#     elif isinstance(loaded_model, trimesh.Trimesh):
#         meshes.append(loaded_model)
#
#     split_meshes = []
#     for mesh in meshes:
#         parts = mesh.split(only_watertight=False)
#         split_meshes.extend(parts)
#
#     print(f"🔧 连通域拆分后得到 {len(split_meshes)} 个子mesh")
#
#     return split_meshes
#
#
# # ===================== 主流程 =====================
# def split_exact_physical(input_obj, output_dir, min_thickness=0.05):
#     loaded = trimesh.load(input_obj)
#     print(f"✅ 加载成功: {input_obj}")
#
#     os.makedirs(output_dir, exist_ok=True)
#
#     meshes = load_all_original_meshes(loaded)
#     print(f"📦 子mesh数量: {len(meshes)}")
#
#     print("🔍 正在空间聚类（不是接触）...")
#     merged_models = cluster_meshes(meshes, tol=0.3)
#
#     print(f"✅ 聚类得到 {len(merged_models)} 个物体")
#
#     count = 0
#
#     for i, model in enumerate(merged_models):
#         # print(f"\n━━━━━━ 处理模型 {i + 1} ━━━━━━")
#
#         processed = ensure_thickness(model, min_thickness)
#
#         if len(processed.vertices) < 4:
#             print("    ❌ 跳过（太小）")
#             continue
#
#         count += 1
#         out = os.path.join(output_dir, f"pavilion_{count:03d}.obj")
#         processed.export(out)
#         # model.export(out)
#
#         # print(f"    ✅ 导出: {out}")
#
#     print(f"\n🎉 完成！输出 {count} 个obj模型")
#
#
# # ===================== CLI =====================
# if __name__ == "__main__":
#     if len(sys.argv) < 3:
#         print("用法: python script.py input.obj output_dir [thickness]")
#         sys.exit(1)
#
#     input_path = sys.argv[1]
#     output_dir = sys.argv[2]
#     # min_thickness = float(sys.argv[3]) if len(sys.argv) > 3 else 0.05
#     # split_exact_physical(input_path, output_dir, min_thickness)
#     split_exact_physical(input_path, output_dir)
import trimesh
import numpy as np
import os
import sys


# ===================== 法线统一 =====================
def fix_mesh_normals(mesh):
    if mesh.is_empty:
        return mesh

    mesh.remove_unreferenced_vertices()

    # ===== 兼容 remove_degenerate_faces =====
    if hasattr(mesh, "remove_degenerate_faces"):
        mesh.remove_degenerate_faces()
    else:
        # 👉 老版本写法
        mask = mesh.nondegenerate_faces()
        mesh.update_faces(mask)
        mesh.remove_unreferenced_vertices()

    # ===== 修复法线 =====
    try:
        mesh.fix_normals()
    except:
        pass

    return mesh


# ===================== 稳定 PCA 法向 =====================
def compute_stable_normal(mesh):
    if len(mesh.vertices) < 3:
        return np.array([0, 0, 1])

    cov = np.cov(mesh.vertices.T)
    eigvals, eigvecs = np.linalg.eigh(cov)

    normal = eigvecs[:, np.argmin(eigvals)]

    # 👉 用平均法线来统一方向（关键！）
    if mesh.face_normals is not None and len(mesh.face_normals) > 0:
        avg_normal = mesh.face_normals.mean(axis=0)
        if np.dot(normal, avg_normal) < 0:
            normal = -normal

    return normal / (np.linalg.norm(normal) + 1e-8)


# ===================== 安全加厚 =====================
def extrude_safe(mesh, distance):
    if len(mesh.vertices) < 3:
        return mesh

    mesh = fix_mesh_normals(mesh)

    normal = compute_stable_normal(mesh)

    v_bottom = mesh.vertices.copy()
    v_top = v_bottom + normal * distance

    f_bottom = mesh.faces.copy()
    f_top = np.fliplr(f_bottom)

    # ===== 兼容 boundary edges =====
    edges = mesh.edges_unique
    internal_edges = mesh.face_adjacency_edges

    internal_set = set(map(tuple, np.sort(internal_edges, axis=1)))

    boundary_edges = []
    for e in edges:
        if tuple(sorted(e)) not in internal_set:
            boundary_edges.append(e)

    edges = np.array(boundary_edges)

    offset = len(v_bottom)
    side_faces = []

    for v0, v1 in edges:
        # ✅ 修正 winding（非常关键）
        side_faces.append([v0, v1, v1 + offset])
        side_faces.append([v0, v1 + offset, v0 + offset])

    if len(side_faces) == 0:
        side_faces = np.zeros((0, 3), dtype=np.int64)
    else:
        side_faces = np.array(side_faces)

    vertices = np.vstack([v_bottom, v_top])
    faces = np.vstack([f_bottom, f_top + offset, side_faces])

    new_mesh = trimesh.Trimesh(vertices=vertices, faces=faces)

    new_mesh = fix_mesh_normals(new_mesh)

    return new_mesh


# ===================== 厚度检测 =====================
def compute_thickness(mesh, normal):
    proj = mesh.vertices @ normal
    return proj.max() - proj.min()


def ensure_thickness(mesh, min_thickness=0.05):
    if mesh.is_empty or len(mesh.vertices) < 3:
        return mesh

    mesh = fix_mesh_normals(mesh)

    normal = compute_stable_normal(mesh)
    thickness = compute_thickness(mesh, normal)

    if thickness >= min_thickness:
        return mesh

    print(f"    → 当前厚度={thickness:.6f}，开始加厚")

    delta = min_thickness - thickness

    # ✅ 只向“外侧”挤出
    mesh_out = extrude_safe(mesh, delta)

    return mesh_out


# ===================== 距离判断 =====================
def check_mesh_close(mesh1, mesh2, tol):
    b1_min, b1_max = mesh1.bounds
    b2_min, b2_max = mesh2.bounds

    dist = np.maximum(0, np.maximum(b1_min - b2_max, b2_min - b1_max))
    dist = np.linalg.norm(dist)

    return dist < tol


# ===================== 聚类 =====================
def cluster_meshes(meshes, tol):
    groups = []

    for mesh in meshes:
        assigned = False

        for group in groups:
            for g in group:
                if check_mesh_close(mesh, g, tol):
                    group.append(mesh)
                    assigned = True
                    break
            if assigned:
                break

        if not assigned:
            groups.append([mesh])

    result = []
    for g in groups:
        combined = trimesh.util.concatenate(g)
        combined = fix_mesh_normals(combined)
        result.append(combined)

    return result


# ===================== 加载 + split =====================
def load_all_original_meshes(loaded_model):
    meshes = []

    if isinstance(loaded_model, trimesh.Scene):
        for geom in loaded_model.geometry.values():
            if isinstance(geom, trimesh.Trimesh):
                meshes.append(geom)

    elif isinstance(loaded_model, trimesh.Trimesh):
        meshes.append(loaded_model)

    split_meshes = []
    for mesh in meshes:
        mesh = fix_mesh_normals(mesh)
        parts = mesh.split(only_watertight=False)
        split_meshes.extend(parts)

    print(f"🔧 连通域拆分后得到 {len(split_meshes)} 个子mesh")

    return split_meshes


# ===================== 主流程 =====================
def split_exact_physical(input_obj, output_dir, min_thickness=0.05):
    loaded = trimesh.load(input_obj)
    print(f"✅ 加载成功: {input_obj}")

    os.makedirs(output_dir, exist_ok=True)

    meshes = load_all_original_meshes(loaded)
    print(f"📦 子mesh数量: {len(meshes)}")

    print("🔍 正在空间聚类...")
    merged_models = cluster_meshes(meshes, tol=0.08)

    print(f"✅ 聚类得到 {len(merged_models)} 个物体")

    count = 0

    for i, model in enumerate(merged_models):

        processed = ensure_thickness(model, min_thickness)

        if len(processed.vertices) < 4:
            continue

        processed = fix_mesh_normals(processed)

        count += 1
        out = os.path.join(output_dir, f"pavilion_{count:03d}.obj")
        processed.export(out)

    print(f"\n🎉 完成！输出 {count} 个obj模型")


# ===================== CLI =====================
if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("用法: python script.py input.obj output_dir")
        sys.exit(1)

    input_path = sys.argv[1]
    output_dir = sys.argv[2]

    split_exact_physical(input_path, output_dir)