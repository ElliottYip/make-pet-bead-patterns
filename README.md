# Make Pet Bead Patterns

一个用于 Codex 的开源 Skill：把宠物照片转换成可实际制作的拼豆图纸，并在生成前先询问所需拼板尺寸。

## 功能

- 接受 HEIC、JPG、JPEG、PNG 宠物照片
- 首先询问尺寸，支持一次选择多个尺寸，例如 15×15、20×20、25×25、30×30
- 输出严格对应目标拼板尺寸的网格
- 提供格内数字编号版、MARD 色号版、成品预览图和用量 CSV
- 默认使用纯白背景；狗狗身体以外的白色区域留空，白色毛发仍保留为白色拼豆
- 内置 MARD 5 mm 色卡映射和颜色用量统计

## 安装

使用 Codex 的 skill-installer 从以下目录安装：

    https://github.com/ElliottYip/make-pet-bead-patterns/tree/main/skills/make-pet-bead-patterns

也可以手动复制：

    cp -R skills/make-pet-bead-patterns ~/.codex/skills/

安装后在 Codex 中使用：

    $make-pet-bead-patterns

Skill 会先询问所需尺寸，再根据照片生成图纸。

## 命令行使用

要求 Python 3.9+ 与 Pillow。处理 HEIC 时建议安装 libheif 提供的 heif-convert。

    python3 skills/make-pet-bead-patterns/scripts/make_bead_pattern.py \
      --source pet.png \
      --output-dir output \
      --name my-pet \
      --size 15x15 \
      --size 20x20 \
      --size 25x25 \
      --size 30x30

输入图像最好已经完成主体抠图并带透明背景；在 Codex 工作流中，Skill 会先完成照片选择、主体隔离和构图，再调用脚本生成图纸。

## 输出内容

每个尺寸会生成：

- 数字编号图纸 PNG
- MARD 色号图纸 PNG
- 拼豆成品预览 PNG
- 颜色编号、MARD 色号及数量 CSV

## 隐私

本仓库不包含任何用户宠物照片或由照片生成的图纸样本。

## License

项目代码与 Skill 采用 MIT License。内置 MARD 色卡数据来源及其许可证见 references/third-party.md 和 references/beadcolors-LICENSE.txt。

---

An open-source Codex skill that converts pet photos into practical, numbered fuse-bead patterns. It asks for the target board size first, supports multiple exact grid sizes, and exports numbered charts, MARD color-code charts, previews, and bead-count CSV files.
