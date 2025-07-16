import { generateQuestion,generateAnswer } from '../../services/apiService.js';

export function setupQuestionSidebar(contentText) {
    let questionsContainer = document.getElementById('questions-container');
    if (!questionsContainer) {
        // 创建问题容器元素
        questionsContainer = document.createElement('div');
        questionsContainer.id = 'questions-container';
        questionsContainer.style.cssText = 'width: 100%; height: 100%; overflow-y: auto;';
        
        // 获取或创建侧边栏容器
        let sidebar = document.getElementById('question-sidebar');
        if (!sidebar) {
            sidebar = document.createElement('div');
            sidebar.id = 'question-sidebar';
            document.body.appendChild(sidebar);
        }
        
        sidebar.appendChild(questionsContainer);
        console.log('动态创建问题容器');
    }

    function addStepMessage(message) {
        const stepElement = document.createElement('div');
        stepElement.style.cssText = 'color: #6c757d; padding: 8px; margin-bottom: 8px; font-size: 0.9em; border-left: 3px solid #d1d5db;';
        stepElement.textContent = message;
        questionsContainer.appendChild(stepElement);
        // 自动滚动到底部以显示最新消息
        questionsContainer.scrollTop = questionsContainer.scrollHeight;
    }

    if (!contentText) {
        const textStatus = document.createElement('div');
        textStatus.style.cssText = 'color: #dc3545; padding: 10px; background: #f8d7da; border-radius: 4px; margin-bottom: 15px;';
        textStatus.textContent = `文本内容提取失败 (长度: ${contentText ? contentText.length : 0}字符)`;
        questionsContainer.appendChild(textStatus);
    }

    if (contentText && contentText.length < 50) {
        console.error('提取到的文本内容过短，无法生成问题');
        questionsContainer.innerHTML = '<p style="color: #f59e0b;">内容过短，无法生成问题</p>';
        return;
    }

    // 在侧边栏显示文本内容预览
    if (contentText) {
        const textPreview = document.createElement('div');
        textPreview.style.cssText = 'margin: 15px 0; padding: 10px; background: #f8f9fa; border-radius: 4px; font-size: 14px; max-height: 100px; overflow-y: auto;';
        textPreview.innerHTML = `<strong>文本预览:</strong><br>${contentText.substring(0, 200)}${contentText.length > 200 ? '...' : ''}`;
        questionsContainer.appendChild(textPreview);

        console.log('文本内容前200字符:', contentText.substring(0, 200));
        console.log('问题容器是否存在:', !!questionsContainer);

        try {
            generateQuestion(contentText);
            addStepMessage('API调用完成，问题生成成功');
        } catch (error) {
            addStepMessage('API调用失败: ' + error.message);
            const errorEl = document.createElement('div');
            errorEl.style.cssText = 'color: #721c24; padding: 10px; background: #f8d7da; border-radius: 4px; margin: 10px 0;';
            errorEl.textContent = '问题生成失败: ' + error.message;
            questionsContainer.appendChild(errorEl);
        }

        console.log('问题生成完成');
        if (questionsContainer.children.length === 0) {
            console.warn('问题生成成功但未返回任何问题');
            questionsContainer.innerHTML = '<p style="color: #f59e0b;">未生成任何问题，请尝试其他页面</p>';
        }
    }
}