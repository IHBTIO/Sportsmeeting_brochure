# 运动会秩序册生成工具

学校运动会秩序册自动生成工具：从报名表（Excel/CSV）导入数据，
经智能识别、人工审查、冲突检测，一键排版生成 Word 格式秩序册。

- **版本**：v2.6.0
- **作者**：hbhbhbhbhvb
- **开源地址**：见 `app/version.py` 中的 GITHUB 常量

## 功能特性

- 多类型数据导入：报名信息 / 校纪录 / 体质健康标准 / 其他表格，
  均带字段映射，额外列自动忽略，支持覆盖/追加
- 智能识别：项目名、班级名、人名、性别自动规范化，
  置信分分级（自动通过/建议核对/需人工审查），开关与阈值可调
- 人工审查：按问题分组查看、批量忽略、逐条修改、手动增删
- 项目管理：内置 40+ 常见项目，可自定义/禁用/删除，
  时间轴预览，一键冲突检测（项目时间重叠=黄色，运动员冲突=红色）
- 班级管理：号码范围自动计算（全校累计 / 班内独立）
- 秩序册模块：13 个模块自由勾选，长文本支持 txt/docx 导入与拖拽，
  条款支持预设快速填写
- Word 输出：目录自动生成，黑体标题 / 宋体正文 / 表格线框

## 环境要求

Python 3.9+，Windows / macOS / Linux

## 安装

bash
git clone https://github.com/IHBTIO/Sportsmeeting_brochure
cd sport-meet
pip install -r requirements.txt


## 使用

bash
python main.py


流程：数据导入 → 人工审查 → 项目/赛程管理 → 班级管理 →
秩序册模块 → 生成秩序册。测试数据可运行 `python make_test_data.py`。

## 二次开发

- 修改作者名/开源地址：`app/version.py` 顶部常量
- 扩充识别词库：`app/recognizer.py`
- 新增预设条款：`app/presets.py`
- 调整 Word 排版：`app/docgen.py`

## 许可证

MIT License，详见 LICENSE。
