<!--
 * @Author: fbee3157 fbee3157@outlook.com
 * @Date: 2026-05-12 16:54:00
 * @LastEditors: fbee3157 fbee3157@outlook.com
 * @LastEditTime: 2026-05-12 16:54:10
 * @FilePath: \TARS-chat\CONTRIBUTING.MD
 * @Description: 这是默认设置,请设置`customMade`, 打开koroFileHeader查看配置 进行设置: https://github.com/OBKoro1/koro1FileHeader/wiki/%E9%85%8D%E7%BD%AE
-->
# 贡献指南

感谢你对 TARS-chat 感兴趣!欢迎以任何形式参与:

## 报告 Bug / 提需求
请到 [Issues](https://github.com/kemomi/TARS-chat/issues) 提交,使用以下模板:

```
**环境**
- 树莓派型号:
- OS 版本:
- Python 版本:

**复现步骤**
1. ...
2. ...

**期望行为**

**实际行为**

**日志**(`/var/log/tars-chat.log`)
```

## 提交代码

1. Fork 仓库
2. 创建特性分支: `git checkout -b feat/your-feature`
3. 提交: `git commit -m "feat: add xxx"` (建议遵循 [Conventional Commits](https://www.conventionalcommits.org/))
4. 推送并发 PR

## 代码风格

- Python: 遵循 PEP 8,推荐 `black` + `ruff`
- JS: 使用 2 空格缩进
- 公共函数请加 docstring

## 本地开发

不接树莓派也能调试:

```bash
cd firmware
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

服务器会以 mock 模式启动舵机(只打日志),Web 控制台依然可用。