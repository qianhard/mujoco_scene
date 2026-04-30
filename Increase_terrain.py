import xml.etree.ElementTree as xml_et
import numpy as np
import noise
import cv2


def list_to_str(v):
    return " ".join(map(str, v))


def euler_to_quat(r, p, y):
    cr, sr = np.cos(r/2), np.sin(r/2)
    cp, sp = np.cos(p/2), np.sin(p/2)
    cy, sy = np.cos(y/2), np.sin(y/2)

    return [
        cr*cp*cy + sr*sp*sy,
        sr*cp*cy - cr*sp*sy,
        cr*sp*cy + sr*cp*sy,
        cr*cp*sy - sr*sp*cy
    ]


def rot2d(x, y, yaw):
    return (
        x*np.cos(yaw) - y*np.sin(yaw),
        x*np.sin(yaw) + y*np.cos(yaw)
    )


class TerrainAdder:

    def __init__(self, xml_path):
        self.tree = xml_et.parse(xml_path)
        self.root = self.tree.getroot()
        self.worldbody = self.root.find("worldbody")
        self.asset = self.root.find("asset")

    # ================= 基础 =================
    def add_box(self, pos, size, yaw=0):
        geom = xml_et.SubElement(self.worldbody, "geom")
        geom.attrib["type"] = "box"
        geom.attrib["pos"] = list_to_str(pos)
        geom.attrib["size"] = list_to_str(0.5 * np.array(size))
        geom.attrib["quat"] = list_to_str(euler_to_quat(0, 0, yaw))

    # ================= 台阶 =================
    def add_stairs(self, pos, yaw=0, params={}):
        step_h = params.get("step_h", 0.15)
        step_d = params.get("step_d", 0.3)
        steps = params.get("steps", 10)
        width = params.get("width", 2.0)

        x0, y0, z0 = pos

        # 上
        for i in range(steps):
            lx = i * step_d
            lz = (i + 0.5) * step_h

            x, y = rot2d(lx, 0, yaw)
            self.add_box([x+x0, y+y0, z0+lz],
                         [step_d, width, step_h], yaw)

        # 平台
        top_z = z0 + steps * step_h
        lx = steps * step_d + 0.6
        x, y = rot2d(lx, 0, yaw)
        self.add_box([x+x0, y+y0, top_z],
                     [1.2, width, step_h], yaw)

        # 下
        for i in range(steps):
            lx = steps * step_d + 1.2 + i * step_d
            lz = top_z - (i + 0.5) * step_h

            x, y = rot2d(lx, 0, yaw)
            self.add_box([x+x0, y+y0, z0+lz],
                         [step_d, width, step_h], yaw)

    # ================= 斜坡 =================
    def add_slope(self, pos, yaw=0, params={}):
        length = params.get("length", 6)
        height = params.get("height", 1.5)
        width = params.get("width", 2)

        angle = np.arctan(height / length)
        x0, y0, z0 = pos

        # 上坡
        lx = length/2
        lz = height/2
        x, y = rot2d(lx, 0, yaw)

        self.add_box([x+x0, y+y0, z0+lz],
                     [length, width, 0.1],
                     yaw)

        # 平台
        lx = length + 1
        x, y = rot2d(lx, 0, yaw)

        self.add_box([x+x0, y+y0, z0+height],
                     [2, width, 0.1],
                     yaw)

        # 下坡
        lx = length*1.5 + 2
        x, y = rot2d(lx, 0, yaw)

        self.add_box([x+x0, y+y0, z0+height/2],
                     [length, width, 0.1],
                     yaw)

    # ================= 粗糙 =================
    def add_rough(self, pos, yaw=0, params={}):
        size = params.get("area", [5, 5])
        grid = params.get("grid", [8, 8])

        dx = size[0] / grid[0]
        dy = size[1] / grid[1]

        for i in range(grid[0]):
            for j in range(grid[1]):
                lx = i * dx
                ly = j * dy - size[1]/2

                x, y = rot2d(lx, ly, yaw)
                h = np.random.uniform(0.05, 0.3)

                self.add_box([x+pos[0], y+pos[1], pos[2]+h/2],
                             [dx*0.9, dy*0.9, h],
                             yaw)

    # ================= Perlin =================
    def add_perlin(self, pos, yaw=0, params={}):
        size = params.get("size", [6, 6])

        img = np.zeros((128, 128), dtype=np.uint8)
        for i in range(128):
            for j in range(128):
                n = noise.pnoise2(i/30, j/30)
                img[j, i] = int((n+1)*127)

        name = f"hfield_{np.random.randint(10000)}"
        file = f"{name}.png"
        cv2.imwrite('mesh/'+file, img)
        cv2.imwrite(file, img)
        hfield = xml_et.SubElement(self.asset, "hfield")
        hfield.attrib["name"] = name
        hfield.attrib["size"] = list_to_str(
            [size[0]/2, size[1]/2, 0.5, 0.5]
        )
        hfield.attrib["file"] = file

        geom = xml_et.SubElement(self.worldbody, "geom")
        geom.attrib["type"] = "hfield"
        geom.attrib["hfield"] = name
        geom.attrib["pos"] = list_to_str(pos)

    # ================= 调度 =================
    def add_one(self, item, base_pos):
        t = item["type"]
        yaw = item.get("yaw", 0)
        params = item.get("params", {})

        if t == "stairs":
            self.add_stairs(base_pos, yaw, params)

        elif t == "slope":
            self.add_slope(base_pos, yaw, params)

        elif t == "rough":
            self.add_rough(base_pos, yaw, params)

        elif t == "perlin":
            self.add_perlin(base_pos, yaw, params)

    def add_terrain(self, config):
        for item in config:

            base = item["pos"]

            # -------- 单个 --------
            if "repeat" not in item:
                self.add_one(item, base)

            # -------- 重复 --------
            else:
                rep = item["repeat"]

                if rep["mode"] == "grid":
                    for i in range(rep["nx"]):
                        for j in range(rep["ny"]):
                            dx = i * rep["dx"]
                            dy = j * rep["dy"]

                            pos = [
                                base[0] + dx,
                                base[1] + dy,
                                base[2]
                            ]
                            self.add_one(item, pos)

                elif rep["mode"] == "list":
                    for offset in rep["offsets"]:
                        pos = [
                            base[0] + offset[0],
                            base[1] + offset[1],
                            base[2] + offset[2]
                        ]
                        self.add_one(item, pos)

    def save(self, path):
        self.tree.write(path)


# ================= 使用示例 =================
if __name__ == "__main__":

    config = [

        # 台阶（旋转+自定义尺寸）
        {
            "type": "stairs",
            "pos": [40, 0, -1],
            "yaw": 0.5,
            "params": {"steps": 12, "width": 3}
        },
        {
            "type": "stairs",
            "pos": [40, 20, -1],
            "yaw": 0.5,
            "params": {"steps": 12, "width": 3}
        },

        # 多个斜坡（grid）
        {
            "type": "slope",
            "pos": [40, 0, -1],
            "repeat": {
                "mode": "grid",
                "nx": 3,
                "ny": 1,
                "dx": 10,
                "dy": 0
            }
        },

        # 粗糙地面阵列
        {
            "type": "rough",
            "pos": [80, 0, -1],
            "repeat": {
                "mode": "grid",
                "nx": 2,
                "ny": 2,
                "dx": 8,
                "dy": 8
            }
        },

        # 随机分布地形
        {
            "type": "perlin",
            "pos": [120, 0, -1],
            "repeat": {
                "mode": "list",
                "offsets": [
                    [0, 0, 0],
                    [10, 0, 0],
                    [20, 5, 0]
                ]
            }
        }
    ]

    ta = TerrainAdder("test_scene_v2_updated_v2.xml")
    ta.add_terrain(config)
    ta.save("scene_with_terrain.xml")

    print("✅ 完成")