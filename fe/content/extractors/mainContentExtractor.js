// 核心内容提取函数
function extractMainContent() {
    const element = extractMainContentElement();
    if (!element) return '';
    const clone = element.cloneNode(true);
    clone.querySelectorAll('script, style, noscript').forEach(el => el.remove());
    const cleanedText = clone.textContent.replace(/\s+/g, ' ').trim();
    return cleanedText; 
}

// 提取主内容元素
function extractMainContentElement() {
    console.log('开始提取主内容元素');
    // 尝试多种内容选择策略
    let selectors = [
        'main',                  // 标准main标签
        'article',               // 文章标签
        '#main-content',         // 常见主内容ID
        '.main-content',         // 常见主内容类
        '#content',              // 内容容器
        '.post-content',         // 文章内容类
        'div[role="main"]',     // ARIA主内容角色
        '.article-content',      // 新增: 文章内容类
        '.blog-post',            // 新增: 博客文章类
        '.entry-content',        // 新增: 条目内容类
        '#article',              // 新增: 文章ID
        'body > div:not([class*="header"]):not([class*="footer"]):not([class*="nav"])' // 排除常见导航/页脚的body直接子元素
    ];

    for (const selector of selectors) {
        const element = document.querySelector(selector);
        if (element) {
            // 检查元素是否包含足够文本
            if (element.textContent.trim().length > 100) {
                console.log(`使用选择器成功找到主内容: ${selector}`);
                return element;
            }
            console.log(`选择器${selector}找到元素但文本过短: ${element.textContent.trim().length}字符`);
        }
    }

    // 如果没有找到特定元素，尝试分析页面结构
    console.log('未找到特定主内容元素，尝试分析页面结构');
    const allElements = Array.from(document.body.children);
    let bestCandidate = null;
    let maxTextLength = 0;

    function getTextLength(element) {
        return element.textContent.trim().length;
    }

    function isNotNoise(tagName) {
        return !['SCRIPT', 'STYLE', 'LINK', 'META', 'NOSCRIPT', 'HEADER', 'FOOTER', 'NAV'].includes(tagName);
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

    // 最后的备选方案 - 使用body（会包含较多噪音）
    console.log('无法找到合适的主内容元素，使用body作为备选');
    return document.body;
}

// 提取并验证页面主内容
// function extractAndValidateContent() {
//     try {
//         const mainContent = extractMainContentElement();
//         console.log('提取到的主内容元素:', mainContent);
        
//         if (mainContent) {
//             console.log('主内容标签名:', mainContent.tagName);
//             console.log('主内容文本长度:', mainContent.textContent.length);
//             console.log('主内容HTML片段:', mainContent.innerHTML.substring(0, 200));
//         }

//         if (!mainContent) {
//             console.error('无法提取页面主内容');
//             showErrorNotification('提取失败', '无法提取页面主要内容，请尝试其他网页。');
//             return null;
//         }
        
//         return mainContent;
//     } catch (error) {
//         console.error('提取页面主内容时发生异常:', error);
//         const errorContainer = document.createElement('div');
//         errorContainer.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: #ff4444; color: white; display: flex; justify-content: center; align-items: center; font-size: 24px; z-index: 999999;';
//         errorContainer.textContent = '错误：提取页面内容时发生异常，请尝试其他网页。';
//         document.body.appendChild(errorContainer);
//         return null;
//     }
// }

export { extractMainContentElement, extractMainContent, extractAndValidateContent };