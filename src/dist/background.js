console.log("Service Worker激活成功");
chrome.runtime.onInstalled.addListener(() => {
  console.log("扩展安装/更新完成");
});
chrome.action.onClicked.addListener(async (tab) => {
  try {
    const [tab2] = await chrome.tabs.query({
      active: true,
      currentWindow: true
    });
    if (!tab2) {
      throw new Error("未找到活动标签页");
    }
    const contentResponse = await chrome.tabs.sendMessage(tab2.id, { action: "extractMainContent" });
    if (!contentResponse || !contentResponse.content) {
      throw new Error("未能提取页面主内容");
    }
    await chrome.tabs.sendMessage(tab2.id, {
      action: "enableImmersiveMode",
      content: contentResponse.content
    });
    console.log("沉浸式阅读模式已启用");
  } catch (error) {
    console.error("操作失败:", error);
    if (chrome.notifications) {
      chrome.notifications.create({
        type: "basic",
        iconUrl: "images/icon48.png",
        title: "操作失败",
        message: "无法启用沉浸式阅读模式: " + error.message
      });
    }
  }
});
