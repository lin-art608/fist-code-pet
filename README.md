# 桌宠 v10

v10 是把 v9 的 64 帧舞蹈验证方案接入完整主程序后的源码版本。目录完全独立，不会读取 v8 或 v9 文件，也不再打包 EXE。

## 功能

- 待机、挥手、跳跃、64 帧舞蹈、独立喂食动作。
- 右键打开菜单；双击喂食；按住人物拖动；Esc 或菜单退出。
- 属性、存档、自动说话及 Canvas 内气泡均已迁移到 Qt。
- Qt 逐像素透明，不使用绿色色键；命令菜单退出后不会留下 Tk 残影或 Tcl 错误框。
- 所有动作使用 400×500 画布和同一参考人物比例。站立动作统一约 460 像素高；跳跃只保留真实离地位移，不改变缩放。
- 待机、挥手、跳跃和喂食由本目录高分辨率动作表通过 `isnet-anime` 语义模型重新生成柔和 Alpha，避免误删白袜、衣领和花束包装；舞蹈使用 v9 验证通过的 64 帧。

## 运行

1. `python -m pip install -r requirements.txt`
2. 双击 `启动桌宠v10.vbs`

动作图片已经生成，正常运行不需要 NumPy、Pillow 或 SciPy。只有重新构建非舞蹈帧时才需要：

1. `python -m pip install -r requirements-build.txt`
2. `python tools/build_main_frames.py`

源图片、动作帧、代码和依赖声明全部位于 v10 内。存档保存在 `pet_save.json`。
