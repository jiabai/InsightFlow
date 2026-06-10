// 定义原始页面状态接口
interface OriginalPageState {
    headHTML: string;
    bodyHTML: string;
}

let originalPageState: OriginalPageState | null = null;

// 启用沉浸式阅读模式
async function enableImmersiveMode(content: string): Promise<void> {
    if (!content || content.trim().length < 500) {
        console.warn('主内容字数不足500，沉浸式阅读模式不生效');
        return;
    }
    // 保存原始页面状态
    originalPageState = {
        headHTML: document.head.innerHTML,
        bodyHTML: document.body.innerHTML
    };

    const tempElement = document.createElement('p');
    tempElement.textContent = content;
    const mainContentElement: HTMLElement = tempElement;

    const immersiveContainer = createImmersiveContainer(mainContentElement);
    document.body.appendChild(immersiveContainer);

    console.log('immersiveContainer HTML内容:', immersiveContainer.innerHTML);
    console.log('immersiveContainer 文本内容:', immersiveContainer.textContent);
    // 应用样式
    applyImmersiveStyles();

    // 创建关闭按钮
    createCloseButton();

    console.log('沉浸式阅读模式已成功启用');
}

// 退出沉浸式阅读模式
function disableImmersiveMode(): void {
    // 移除所有沉浸式模式相关元素
    const elementsToRemove = [
        'immersive-reading-style',
        'immersive-container',
        'question-sidebar',
        'immersive-close'
    ];
    elementsToRemove.forEach(id => {
        const element = document.getElementById(id);
        if (element) element.remove();
    });

    // 恢复页面原始状态
    if (originalPageState) {
        document.head.innerHTML = originalPageState.headHTML;
        document.body.innerHTML = originalPageState.bodyHTML;
    }

    console.log('沉浸式阅读模式已完全关闭');
}

// 创建沉浸式阅读容器
function createImmersiveContainer(mainContent: HTMLElement): HTMLElement {
    const container = document.createElement('div');
    container.id = 'immersive-container';

    // 克隆主内容到容器
    const clonedContent = mainContent.cloneNode(true) as HTMLElement;

    clonedContent.classList.remove('hidden', 'd-none', 'visually-hidden', 'sr-only');
    clonedContent.style.display = 'block !important';
    clonedContent.style.visibility = 'visible !important';

    // 内容验证和警告
    if (!clonedContent.textContent || clonedContent.textContent.trim().length === 0) {
        const emptyWarning = document.createElement('div');
        emptyWarning.style.cssText = 'color: #f59e0b; font-size: 18px; padding: 20px; background: #fff3cd; border-radius: 4px;';
        emptyWarning.textContent = '警告：未能从页面提取到可读内容，请尝试其他网页或检查内容提取规则。';
        container.appendChild(emptyWarning);
    }

    // 验证内容长度
    const clonedContentLength = (clonedContent.textContent || '').trim().length;
    console.log('克隆后内容文本长度:', clonedContentLength);

    if (clonedContentLength < 50) {
        const emptyContentWarning = document.createElement('div');
        emptyContentWarning.style.cssText = 'color: #dc3545; padding: 20px; background: #f8d7da; border-radius: 8px; margin: 20px 0; text-align: center;';
        emptyContentWarning.innerHTML = '<strong>无法显示内容</strong><br>页面内容过短或无法识别，请尝试选择其他页面或手动选择文本。';
        container.appendChild(emptyContentWarning);
    } else {
        container.appendChild(clonedContent);
    }

    return container;
}

// 应用沉浸式阅读样式
function applyImmersiveStyles(): void {
    const style = document.createElement('style');
    style.id = 'immersive-reading-style';
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
    console.log('沉浸式阅读样式已添加');
}

// 创建关闭按钮
function createCloseButton(): void {
    const closeBtn = document.createElement('button');
    closeBtn.id = 'immersive-close';
    closeBtn.textContent = '退出沉浸式阅读';
    closeBtn.addEventListener('click', disableImmersiveMode);
    document.body.appendChild(closeBtn);
}

export { disableImmersiveMode, enableImmersiveMode };