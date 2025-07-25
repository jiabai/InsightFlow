// 在background.js顶部添加激活日志
console.log('Service Worker激活成功');

chrome.runtime.onInstalled.addListener(() => {
  console.log('扩展安装/更新完成');
});

// 监听插件按钮点击事件 - 触发沉浸式阅读模式
chrome.action.onClicked.addListener(async (tab) => {
    try {
        const [tab] = await chrome.tabs.query({
            active: true,
            currentWindow: true
        });
        if (!tab) {
            throw new Error('未找到活动标签页');
        }
        // 发送消息请求提取页面主内容
        const contentResponse = await chrome.tabs.sendMessage(tab.id, { action: 'extractMainContent' });
        if (!contentResponse || !contentResponse.content) {
            throw new Error('未能提取页面主内容');
        }

        // 打印提取到的内容
        // console.log('提取到的页面内容:', contentResponse.content);

        // 进入沉浸式阅读模式
        await chrome.tabs.sendMessage(tab.id, {
            action: 'enableImmersiveMode',
            content: contentResponse.content
        });
        console.log('沉浸式阅读模式已启用');
    } catch (error) {
        console.error('操作失败:', error);
        if (chrome.notifications) {
            chrome.notifications.create({
                type: 'basic',
                iconUrl: 'images/icon48.png',
                title: '操作失败',
                message: '无法启用沉浸式阅读模式: ' + error.message
            });
        }
    }
});
