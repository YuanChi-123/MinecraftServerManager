from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    html_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minecraft Server Manager 完整介绍</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        h1 {
            color: #4CAF50;
            margin: 0;
        }
        .nav {
            display: flex;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .nav a {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav a:hover {
            background-color: #367c39;
        }
        .content {
            margin-top: 20px;
        }
        .section {
            margin-bottom: 30px;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
            border-radius: 4px;
        }
        .feature-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }
        .feature-item {
            background-color: #fff;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .code {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
        }
        footer {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }
        .screenshot {
            max-width: 100%;
            border-radius: 4px;
            margin: 15px 0;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Minecraft Server Manager</h1>
            <p>版本 1.0-T202510061206 - 专业的Minecraft服务器管理工具</p>
        </header>

        <div class="nav">
            <a href="#overview">概述</a>
            <a href="#features">核心功能</a>
            <a href="#usage">使用指南</a>
            <a href="#settings">配置选项</a>
            <a href="#faq">常见问题</a>
        </div>

        <div class="content">
            <div id="overview" class="section">
                <h2>概述</h2>
                <p>Minecraft Server Manager是一款功能强大的图形化工具，旨在简化Minecraft服务器的创建、配置和管理过程。无论您是初学者还是有经验的服务器管理员，都能通过本工具轻松管理一个或多个Minecraft服务器。</p>
                <p>工具采用直观的标签页式界面，每个服务器拥有独立的管理面板，让您可以同时监控和操作多个服务器实例。</p>
            </div>

            <div id="features" class="section">
                <h2>核心功能</h2>
                <div class="feature-list">
                    <div class="feature-item">
                        <h3>服务器创建向导</h3>
                        <p>通过简单的步骤引导，快速创建新的Minecraft服务器，支持多种核心类型和版本选择。</p>
                    </div>
                    <div class="feature-item">
                        <h3>多服务器管理</h3>
                        <p>采用标签页式设计，可同时管理多个服务器实例，独立监控和操作每个服务器。</p>
                    </div>
                    <div class="feature-item">
                        <h3>实时控制台</h3>
                        <p>实时显示服务器输出日志，并支持直接输入指令与服务器交互。</p>
                    </div>
                    <div class="feature-item">
                        <h3>资源监控</h3>
                        <p>监控服务器进程的CPU和内存使用情况，帮助您优化服务器性能。</p>
                    </div>
                    <div class="feature-item">
                        <h3>配置文件编辑</h3>
                        <p>内置编辑器，方便修改server.properties等关键配置文件。</p>
                    </div>
                    <div class="feature-item">
                        <h3>启动脚本自定义</h3>
                        <p>可编辑服务器启动脚本，自定义Java参数和启动选项。</p>
                    </div>
                    <div class="feature-item">
                        <h3>服务器状态管理</h3>
                        <p>一键启动、停止和重启服务器，操作简单直观。</p>
                    </div>
                    <div class="feature-item">
                        <h3>配置自动保存</h3>
                        <p>自动保存服务器配置，下次启动时无需重新设置。</p>
                    </div>
                </div>
            </div>

            <div id="usage" class="section">
                <h2>使用指南</h2>
                
                <h3>创建新服务器</h3>
                <ol>
                    <li>点击主界面的"创建服务器"按钮</li>
                    <li>在向导中填写服务器名称和安装路径</li>
                    <li>选择服务器核心类型（如Paper、Spigot等）和版本</li>
                    <li>配置Java路径和内存分配（Xms和Xmx参数）</li>
                    <li>点击"创建"按钮，工具将自动下载并配置服务器</li>
                </ol>

                <h3>添加已有服务器</h3>
                <ol>
                    <li>点击"添加已有服务器"按钮</li>
                    <li>浏览并选择已存在的服务器目录</li>
                    <li>工具将验证目录有效性并创建对应的管理标签页</li>
                </ol>

                <h3>服务器操作</h3>
                <ul>
                    <li><strong>启动</strong>：点击服务器标签页中的"启动"按钮</li>
                    <li><strong>停止</strong>：点击"停止"按钮，工具会先尝试优雅关闭，超时则强制终止</li>
                    <li><strong>重启</strong>：点击"重启"按钮，自动完成停止和启动过程</li>
                    <li><strong>发送指令</strong>：在指令输入框中输入命令并按回车或点击"发送"按钮</li>
                </ul>
            </div>

            <div id="settings" class="section">
                <h2>配置选项</h2>
                
                <h3>服务器核心选择</h3>
                <p>工具支持多种Minecraft服务器核心，包括但不限于：</p>
                <ul>
                    <li>Vanilla（官方原版）</li>
                    <li>Spigot</li>
                    <li>Paper</li>
                    <li>Bukkit</li>
                    <li>Forge</li>
                </ul>

                <h3>Java内存设置</h3>
                <p>合理配置内存参数对服务器性能至关重要：</p>
                <ul>
                    <li><strong>Xms</strong>：初始堆内存大小，建议设置为服务器所需的最小内存</li>
                    <li><strong>Xmx</strong>：最大堆内存大小，根据服务器规模和可用系统内存设置</li>
                </ul>
                <p>示例：对于小型服务器，可设置为Xms=1G，Xmx=2G；对于大型服务器，可适当增加。</p>
            </div>

            <div id="faq" class="section">
                <h2>常见问题</h2>
                
                <h3>Q: 启动服务器时提示"未找到Java路径"怎么办？</h3>
                <p>A: 请确保已安装Java，并在服务器创建向导或服务器设置中正确指定Java可执行文件的路径。</p>
                
                <h3>Q: 如何备份我的服务器数据？</h3>
                <p>A: 建议在服务器停止状态下，手动备份服务器目录中的"world"文件夹（世界数据）和其他重要文件。</p>
                
                <h3>Q: 服务器启动后无响应怎么办？</h3>
                <p>A: 检查控制台输出的错误信息，常见原因包括端口被占用、Java版本不兼容或内存不足。</p>
                
                <h3>Q: 可以同时运行多个服务器吗？</h3>
                <p>A: 可以，每个服务器会在独立的标签页中管理，但需确保系统有足够的资源（CPU和内存）。</p>
            </div>
        </div>

        <footer>
            <p>© 2025 Minecraft Server Manager | 更多帮助请查看工具内的"帮助..."按钮或联系技术支持</p>
        </footer>
    </div>
</body>
</html>
'''
    return render_template_string(html_content)

if __name__ == '__main__':
    app.run(debug=True)

app = Flask(__name__)

@app.route('/')
def index():
    html_content = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Minecraft Server Manager 完整介绍</title>
    <style>
        body {
            font-family: 'Microsoft YaHei', Arial, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }
        .container {
            max-width: 1000px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #4CAF50;
            padding-bottom: 10px;
        }
        h1 {
            color: #4CAF50;
            margin: 0;
        }
        .nav {
            display: flex;
            justify-content: center;
            margin: 20px 0;
            flex-wrap: wrap;
        }
        .nav a {
            display: inline-block;
            padding: 10px 20px;
            margin: 5px;
            background-color: #4CAF50;
            color: white;
            text-decoration: none;
            border-radius: 4px;
            transition: background-color 0.3s;
        }
        .nav a:hover {
            background-color: #367c39;
        }
        .content {
            margin-top: 20px;
        }
        .section {
            margin-bottom: 30px;
            padding: 15px;
            background-color: #f9f9f9;
            border-left: 4px solid #4CAF50;
            border-radius: 4px;
        }
        .feature-list {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-top: 15px;
        }
        .feature-item {
            background-color: #fff;
            padding: 15px;
            border-radius: 6px;
            box-shadow: 0 1px 3px rgba(0,0,0,0.1);
        }
        .code {
            background-color: #2d2d2d;
            color: #f8f8f2;
            padding: 10px;
            border-radius: 4px;
            font-family: 'Courier New', monospace;
            overflow-x: auto;
        }
        footer {
            text-align: center;
            margin-top: 30px;
            color: #666;
            font-size: 0.9em;
        }
        .screenshot {
            max-width: 100%;
            border-radius: 4px;
            margin: 15px 0;
            border: 1px solid #ddd;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>Minecraft Server Manager</h1>
            <p>版本 1.0-T202510061206 - 专业的Minecraft服务器管理工具</p>
        </header>

        <div class="nav">
            <a href="#overview">概述</a>
            <a href="#features">核心功能</a>
            <a href="#usage">使用指南</a>
            <a href="#settings">配置选项</a>
            <a href="#faq">常见问题</a>
        </div>

        <div class="content">
            <div id="overview" class="section">
                <h2>概述</h2>
                <p>Minecraft Server Manager是一款功能强大的图形化工具，旨在简化Minecraft服务器的创建、配置和管理过程。无论您是初学者还是有经验的服务器管理员，都能通过本工具轻松管理一个或多个Minecraft服务器。</p>
                <p>工具采用直观的标签页式界面，每个服务器拥有独立的管理面板，让您可以同时监控和操作多个服务器实例。</p>
            </div>

            <div id="features" class="section">
                <h2>核心功能</h2>
                <div class="feature-list">
                    <div class="feature-item">
                        <h3>服务器创建向导</h3>
                        <p>通过简单的步骤引导，快速创建新的Minecraft服务器，支持多种核心类型和版本选择。</p>
                    </div>
                    <div class="feature-item">
                        <h3>多服务器管理</h3>
                        <p>采用标签页式设计，可同时管理多个服务器实例，独立监控和操作每个服务器。</p>
                    </div>
                    <div class="feature-item">
                        <h3>实时控制台</h3>
                        <p>实时显示服务器输出日志，并支持直接输入指令与服务器交互。</p>
                    </div>
                    <div class="feature-item">
                        <h3>资源监控</h3>
                        <p>监控服务器进程的CPU和内存使用情况，帮助您优化服务器性能。</p>
                    </div>
                    <div class="feature-item">
                        <h3>配置文件编辑</h3>
                        <p>内置编辑器，方便修改server.properties等关键配置文件。</p>
                    </div>
                    <div class="feature-item">
                        <h3>启动脚本自定义</h3>
                        <p>可编辑服务器启动脚本，自定义Java参数和启动选项。</p>
                    </div>
                    <div class="feature-item">
                        <h3>服务器状态管理</h3>
                        <p>一键启动、停止和重启服务器，操作简单直观。</p>
                    </div>
                    <div class="feature-item">
                        <h3>配置自动保存</h3>
                        <p>自动保存服务器配置，下次启动时无需重新设置。</p>
                    </div>
                </div>
            </div>

            <div id="usage" class="section">
                <h2>使用指南</h2>
                
                <h3>创建新服务器</h3>
                <ol>
                    <li>点击主界面的"创建服务器"按钮</li>
                    <li>在向导中填写服务器名称和安装路径</li>
                    <li>选择服务器核心类型（如Paper、Spigot等）和版本</li>
                    <li>配置Java路径和内存分配（Xms和Xmx参数）</li>
                    <li>点击"创建"按钮，工具将自动下载并配置服务器</li>
                </ol>

                <h3>添加已有服务器</h3>
                <ol>
                    <li>点击"添加已有服务器"按钮</li>
                    <li>浏览并选择已存在的服务器目录</li>
                    <li>工具将验证目录有效性并创建对应的管理标签页</li>
                </ol>

                <h3>服务器操作</h3>
                <ul>
                    <li><strong>启动</strong>：点击服务器标签页中的"启动"按钮</li>
                    <li><strong>停止</strong>：点击"停止"按钮，工具会先尝试优雅关闭，超时则强制终止</li>
                    <li><strong>重启</strong>：点击"重启"按钮，自动完成停止和启动过程</li>
                    <li><strong>发送指令</strong>：在指令输入框中输入命令并按回车或点击"发送"按钮</li>
                </ul>
            </div>

            <div id="settings" class="section">
                <h2>配置选项</h2>
                
                <h3>服务器核心选择</h3>
                <p>工具支持多种Minecraft服务器核心，包括但不限于：</p>
                <ul>
                    <li>Vanilla（官方原版）</li>
                    <li>Spigot</li>
                    <li>Paper</li>
                    <li>Bukkit</li>
                    <li>Forge</li>
                </ul>

                <h3>Java内存设置</h3>
                <p>合理配置内存参数对服务器性能至关重要：</p>
                <ul>
                    <li><strong>Xms</strong>：初始堆内存大小，建议设置为服务器所需的最小内存</li>
                    <li><strong>Xmx</strong>：最大堆内存大小，根据服务器规模和可用系统内存设置</li>
                </ul>
                <p>示例：对于小型服务器，可设置为Xms=1G，Xmx=2G；对于大型服务器，可适当增加。</p>
            </div>

            <div id="faq" class="section">
                <h2>常见问题</h2>
                
                <h3>Q: 启动服务器时提示"未找到Java路径"怎么办？</h3>
                <p>A: 请确保已安装Java，并在服务器创建向导或服务器设置中正确指定Java可执行文件的路径。</p>
                
                <h3>Q: 如何备份我的服务器数据？</h3>
                <p>A: 建议在服务器停止状态下，手动备份服务器目录中的"world"文件夹（世界数据）和其他重要文件。</p>
                
                <h3>Q: 服务器启动后无响应怎么办？</h3>
                <p>A: 检查控制台输出的错误信息，常见原因包括端口被占用、Java版本不兼容或内存不足。</p>
                
                <h3>Q: 可以同时运行多个服务器吗？</h3>
                <p>A: 可以，每个服务器会在独立的标签页中管理，但需确保系统有足够的资源（CPU和内存）。</p>
            </div>
        </div>

        <footer>
            <p>© 2025 Minecraft Server Manager | 更多帮助请查看工具内的"帮助..."按钮或联系技术支持</p>
        </footer>
    </div>
</body>
</html>
'''
    return render_template_string(html_content)

if __name__ == '__main__':
    app.run(debug=True, host=9178)