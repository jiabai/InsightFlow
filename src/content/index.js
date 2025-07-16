import { extractMainContent } from './extractors/mainContentExtractor.js';
import { enableImmersiveMode } from './immersive/immersiveReader.js';

console.log("Content script is running on 666 :", window.location.href);

// 消息监听器 - 处理来自background和popup的请求
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
    // 确保sendResponse函数只被调用一次
    let responseSent = false;
    const safeSendResponse = (response) => {
        if (!responseSent) {
            responseSent = true;
            sendResponse(response);
        }
    };

    try {
        if (request.action === 'extractMainContent') {
            const mainContent = extractMainContent();
            if (mainContent) {
                console.log('提取到的主内容不为空，内容长度:', mainContent.length);
            } else {
                console.log('提取到的主内容为空');
            }
            safeSendResponse({ content: mainContent });
            return true;
        }
        else if (request.action === 'enableImmersiveMode') {
            console.log('收到启用沉浸式阅读模式请求');
            enableImmersiveMode(request.content).catch(error => {
                console.error('启用沉浸式阅读模式失败:', error);
                alert('启用沉浸式阅读模式时出错: ' + error.message);
            });
            safeSendResponse({ status: 'immersive mode enabled' });
            return true;
        }
        else {
            safeSendResponse({ error: '未知的action: ' + request.action });
            return false;
        }
    } catch (error) {
        console.error('处理消息时出错:', error);
        safeSendResponse({ error: error.message });
        return false;
    }
});
