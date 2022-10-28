# python robot for go-cqhttp

## Description
一个自开发适用于全平台的QQ机器人，用于对接[go-cqhttp](https://github.com/Mrs4s/go-cqhttp)进行自动处理的python程序，主要用于自用，相较于[Nonebot](https://github.com/nonebot/nonebot2)，此项目更偏向于个人学习和使用，自带指令系统以及简陋直接的程序接口，非常适合上手，通讯部分完全可以依照[go-cqhttp HTTP通讯 API](https://docs.go-cqhttp.org/api/#%E5%9F%BA%E7%A1%80%E4%BC%A0%E8%BE%93)进行操作使用和扩展。

## Usage
- 安装Python3.7或以上
- 使用pip install -r requirements.txt安装程序所需第三方库（如需安装其他模块请额外添加缺失库）
- Windows用户请额外执行 pip install windows-curses
- 启动"start.bat"或者"start.sh"

## Tips
- 该项目主要功能请在后台使用help指令查看
- 请在文件夹module内添加或删除模块，自带6个自用可选模块，拖入module安装依赖后即可启用
- 默认对接的cqhttpHTTP监听地址为"127.0.0.1:5700"，反向HTTP POST地址为"127.0.0.1:5701"，可自行修改config.ini进行调整
- 使用Windows自带的命令提示符无法支持颜色效果,因此Windows默认关闭颜色代码，编辑print_color.py开启
- 模块错误默认采用ifunction.py中simplify_traceback()函数处理，便于debug
- 该项目为轻量化使用未采用curses图形库而采用多线程处理后台IO，因此输入命令时收到的新消息可能覆盖命令的显示

## Features
- 模块化的功能加入
- 基础的类终端交互
- 清晰的界面显示和排版
- Threading多线程处理消息
- 方便的调试接口和错误提示
- 不同用户或群的调用权限等级
- 每个群和用户的独立数据存储
- 方便快捷的随机文本选择和回复
- 对图片信息的终端彩色像素画显示
- 支持大部分常用go-cqhttp接口调用
<img src="example/screenshot-1.png" width="280">
<img src="example/screenshot-2.png" width="280">
<img src="example/screenshot-3.png" width="280">
<img src="example/screenshot-4.png" width="280">
<img src="example/screenshot-5.png" width="280">
<img src="example/screenshot-6.png" width="280">
<img src="example/screenshot-7.png" width="280">
<img src="example/screenshot-8.png" width="280">
<img src="example/screenshot-9.png" width="280">
