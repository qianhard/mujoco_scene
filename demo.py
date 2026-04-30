import mujoco
import mujoco.viewer
import os

# 设置 XML 文件路径
# 如果脚本与 XML 在同一目录，直接写文件名即可
xml_path = 'mujoco_scene.xml'

# 检查文件是否存在
if not os.path.exists(xml_path):
    print(f"错误：找不到文件 '{xml_path}'")
    print(f"当前工作目录: {os.getcwd()}")
    exit(1)

print(f"正在加载模型: {xml_path}")
model = mujoco.MjModel.from_xml_path(xml_path)
data = mujoco.MjData(model)


# 查看纹理数量
print("纹理数量:", model.ntex)
# 查看材质数量
print("材质数量:", model.nmat)
# 查看网格的纹理坐标数量（如有）
mesh_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MESH, "road_mesh")
print("网格顶点数:", model.mesh_vertnum[mesh_id])
print("网格面数:", model.mesh_facenum[mesh_id])
# 检查材质是否关联纹理
mat_id = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_MATERIAL, "road_mat")
print("材质纹理ID:", model.mat_texid[mat_id])
# 启动被动查看器（程序将控制仿真循环）
with mujoco.viewer.launch_passive(model, data) as viewer:
    # 可选：设置相机初始视角
    # viewer.cam.lookat = [0, 0, 1]
    # viewer.cam.distance = 5.0
    # viewer.cam.azimuth = 90
    # viewer.cam.elevation = -20
    # viewer.cam.type = mujoco.mjtCamera.mjCAMERA_FREE
    # viewer.cam.distance = 5.0
    # viewer.cam.azimuth = -180  # 水平角度
    # viewer.cam.elevation = -20  # 俯仰角度
    # viewer.cam.lookat[:] = [0, -200, 0.5]  # 看向场景中心

    while viewer.is_running():
        # 步进仿真物理状态
        mujoco.mj_step(model, data)
        # 同步查看器显示
        viewer.sync()