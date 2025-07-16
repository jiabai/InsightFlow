function extractMainContent() {
  const element = extractMainContentElement();
  if (!element) return "";
  const clone = element.cloneNode(true);
  clone.querySelectorAll("script, style, noscript").forEach((el) => el.remove());
  const cleanedText = clone.textContent.replace(/\s+/g, " ").trim();
  return cleanedText;
}
function extractMainContentElement() {
  console.log("开始提取主内容元素");
  let selectors = [
    "main",
    // 标准main标签
    "article",
    // 文章标签
    "#main-content",
    // 常见主内容ID
    ".main-content",
    // 常见主内容类
    "#content",
    // 内容容器
    ".post-content",
    // 文章内容类
    'div[role="main"]',
    // ARIA主内容角色
    ".article-content",
    // 新增: 文章内容类
    ".blog-post",
    // 新增: 博客文章类
    ".entry-content",
    // 新增: 条目内容类
    "#article",
    // 新增: 文章ID
    'body > div:not([class*="header"]):not([class*="footer"]):not([class*="nav"])'
    // 排除常见导航/页脚的body直接子元素
  ];
  for (const selector of selectors) {
    const element = document.querySelector(selector);
    if (element) {
      if (element.textContent.trim().length > 100) {
        console.log(`使用选择器成功找到主内容: ${selector}`);
        return element;
      }
      console.log(`选择器${selector}找到元素但文本过短: ${element.textContent.trim().length}字符`);
    }
  }
  console.log("未找到特定主内容元素，尝试分析页面结构");
  const allElements = Array.from(document.body.children);
  let bestCandidate = null;
  let maxTextLength = 0;
  function getTextLength(element) {
    return element.textContent.trim().length;
  }
  function isNotNoise(tagName) {
    return !["SCRIPT", "STYLE", "LINK", "META", "NOSCRIPT", "HEADER", "FOOTER", "NAV"].includes(tagName);
  }
  for (const element of allElements) {
    if (!isNotNoise(element.tagName)) continue;
    const textLength = getTextLength(element);
    if (textLength > maxTextLength && textLength > 100) {
      maxTextLength = textLength;
      bestCandidate = element;
    }
  }
  if (bestCandidate) {
    console.log(`通过页面结构分析找到主内容，文本长度: ${maxTextLength}`);
    return bestCandidate;
  }
  console.log("无法找到合适的主内容元素，使用body作为备选");
  return document.body;
}
let originalPageState = null;
async function enableImmersiveMode(content) {
  if (!content || content.trim().length < 500) {
    console.warn("主内容字数不足500，沉浸式阅读模式不生效");
    return;
  }
  originalPageState = {
    headHTML: document.head.innerHTML,
    bodyHTML: document.body.innerHTML
  };
  const tempElement = document.createElement("p");
  tempElement.textContent = content;
  const mainContentElement = tempElement;
  const immersiveContainer = createImmersiveContainer(mainContentElement);
  document.body.appendChild(immersiveContainer);
  console.log("immersiveContainer HTML内容:", immersiveContainer.innerHTML);
  console.log("immersiveContainer 文本内容:", immersiveContainer.textContent);
  applyImmersiveStyles();
  createCloseButton();
  console.log("沉浸式阅读模式已成功启用");
}
function disableImmersiveMode() {
  const elementsToRemove = [
    "immersive-reading-style",
    "immersive-container",
    "question-sidebar",
    "immersive-close"
  ];
  elementsToRemove.forEach((id) => {
    const element = document.getElementById(id);
    if (element) element.remove();
  });
  if (originalPageState) {
    document.head.innerHTML = originalPageState.headHTML;
    document.body.innerHTML = originalPageState.bodyHTML;
  }
  console.log("沉浸式阅读模式已完全关闭");
}
function createImmersiveContainer(mainContent) {
  const container = document.createElement("div");
  container.id = "immersive-container";
  const clonedContent = mainContent.cloneNode(true);
  clonedContent.classList.remove("hidden", "d-none", "visually-hidden", "sr-only");
  clonedContent.style.display = "block !important";
  clonedContent.style.visibility = "visible !important";
  if (clonedContent.textContent.trim().length === 0) {
    const emptyWarning = document.createElement("div");
    emptyWarning.style.cssText = "color: #f59e0b; font-size: 18px; padding: 20px; background: #fff3cd; border-radius: 4px;";
    emptyWarning.textContent = "警告：未能从页面提取到可读内容，请尝试其他网页或检查内容提取规则。";
    container.appendChild(emptyWarning);
  }
  const clonedContentLength = clonedContent.textContent.trim().length;
  console.log("克隆后内容文本长度:", clonedContentLength);
  if (clonedContentLength < 50) {
    const emptyContentWarning = document.createElement("div");
    emptyContentWarning.style.cssText = "color: #dc3545; padding: 20px; background: #f8d7da; border-radius: 8px; margin: 20px 0; text-align: center;";
    emptyContentWarning.innerHTML = "<strong>无法显示内容</strong><br>页面内容过短或无法识别，请尝试选择其他页面或手动选择文本。";
    container.appendChild(emptyContentWarning);
  } else {
    container.appendChild(clonedContent);
  }
  return container;
}
function applyImmersiveStyles() {
  const style = document.createElement("style");
  style.id = "immersive-reading-style";
  style.textContent = `
        body { margin: 0 !important; padding: 0 !important; background-color: #f8fafc !important; }
        #immersive-container { display: block !important; position: fixed !important; top: 0 !important; left: 0 !important; width: 100% !important; height: 100% !important; overflow-y: auto !important; max-width: none !important; margin: 0 !important; padding: 2rem !important; background-color: #e6f7ff !important; border: 2px solid #1890ff !important; color: #333 !important; z-index: 99999 !important; }
        #immersive-container p { font-size: 1.1rem; line-height: 1.8; margin-bottom: 1.5rem; color: #333 !important; }
        #immersive-container h1, h2, h3 { margin-top: 2rem; margin-bottom: 1rem; color: #2c3e50 !important; }
        #immersive-container * { display: block !important; visibility: visible !important; color: inherit !important; }
        #immersive-close { position: fixed; top: 1rem; right: 320px; padding: 0.5rem 1rem; background: #3b82f6; color: white; border: none; border-radius: 4px; cursor: pointer; z-index: 100000; }
        #question-sidebar { position: fixed; right: 0; top: 0; width: 300px; height: 100vh; background: white; padding: 2rem; box-shadow: -2px 0 10px rgba(0,0,0,0.1); overflow-y: auto; z-index: 99998; }
        #question-sidebar h3 { margin-top: 0; color: #2c3e50; }
        .question-card { padding: 12px 15px; background-color: white; border-radius: 8px; border: 1px solid #e2e8f0; cursor: pointer; margin-bottom: 8px; transition: all 0.2s ease; }
        .question-card:hover { border-color: #93c5fd; background-color: #f8fafc; }
        .question-icon { color: #3b82f6; margin-right: 10px; min-width: 20px; text-align: center; }
    `;
  document.head.appendChild(style);
  console.log("沉浸式阅读样式已添加");
}
function createCloseButton() {
  const closeBtn = document.createElement("button");
  closeBtn.id = "immersive-close";
  closeBtn.textContent = "退出沉浸式阅读";
  closeBtn.addEventListener("click", disableImmersiveMode);
  document.body.appendChild(closeBtn);
}
console.log("Content script is running on 666 :", window.location.href);
chrome.runtime.onMessage.addListener(function(request, sender, sendResponse) {
  let responseSent = false;
  const safeSendResponse = (response) => {
    if (!responseSent) {
      responseSent = true;
      sendResponse(response);
    }
  };
  try {
    if (request.action === "extractMainContent") {
      const mainContent = extractMainContent();
      if (mainContent) {
        console.log("提取到的主内容不为空，内容长度:", mainContent.length);
      } else {
        console.log("提取到的主内容为空");
      }
      safeSendResponse({ content: mainContent });
      return true;
    } else if (request.action === "enableImmersiveMode") {
      console.log("收到启用沉浸式阅读模式请求");
      enableImmersiveMode(request.content).catch((error) => {
        console.error("启用沉浸式阅读模式失败:", error);
        alert("启用沉浸式阅读模式时出错: " + error.message);
      });
      safeSendResponse({ status: "immersive mode enabled" });
      return true;
    } else {
      safeSendResponse({ error: "未知的action: " + request.action });
      return false;
    }
  } catch (error) {
    console.error("处理消息时出错:", error);
    safeSendResponse({ error: error.message });
    return false;
  }
});
