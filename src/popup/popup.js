// 添加API服务导入
import { generateQuestion, generateAnswer } from '../services/apiService.js';
const generateBtn = document.getElementById('generateBtn');
const exitBtn = document.getElementById('exitBtn');
const contentArea = document.getElementById('contentArea');
// 添加新闻详情缓存对象
const newsDetailCache = {};
// 修改为let以便重新赋值
let newsList = [];

// 添加独立的API调用方法
async function fetchQuestions(userText) {
  try {
    const response = await generateQuestion(userText);
    return response.questions.map(question => ({
      title: question,
      detail: ""
    }));
  } catch (error) {
    console.error('获取问题失败:', error);
    throw error; // 继续抛出错误让调用方处理
  }
}

// 修改绿色按钮点击事件
generateBtn.onclick = async () => {
  // 显示骨架屏和进度条
  contentArea.innerHTML = `
    <div class="progress-bar"><div class="progress-inner" id="progressInner"></div></div>
    <div class="skeleton-list">
      ${Array(10).fill('<div class="skeleton-item"></div>').join('')}
    </div>
    <div style="text-align:center;color:#aaa;margin-top:10px;">生成问题中...</div>
  `;

  // 立即启动进度条动画
  let progress = 0;
  const progressInner = document.getElementById('progressInner');
  if (!progressInner) {
    console.error('进度条元素未找到');
    return;
  }
  const timer = setInterval(() => {
    progress += Math.random() * 18 + 7;
    if (progress > 100) progress = 100;
    progressInner.style.width = progress + "%";
    if (progress >= 100) {
      clearInterval(timer);
    }
  }, 180);

  try {
    // 调用独立方法获取问题
    newsList = await fetchQuestions("用户选中文本");

    // API调用完成后立即关闭进度条和骨架屏
    clearInterval(timer);
    // 直接显示问题列表，无需等待进度条动画
    showQuestions();
  } catch (error) {
    // 错误处理
    clearInterval(timer);
    contentArea.innerHTML = `<div style="text-align:center;color:red;margin-top:40px;">生成问题失败，请重试</div>`;
  }
};

// 在生成问题项时添加箭头元素
function showQuestions() {
  let html = `<div class="question-list">`;
  newsList.forEach((item, idx) => {
    html += `
      <div class="question-item" data-idx="${idx}" endpoint="generate-answer">
        <div class="question-title">${item.title}</div>
        <div class="question-detail" style="display:none;"></div>
        <div class="arrow"></div> <!-- 添加箭头元素 -->
      </div>
    `;
  });
  html += `</div>`;
  contentArea.innerHTML = html;

  // 添加事件委托到父容器 (修复关键代码)
  contentArea.addEventListener('click', async function(e) {
    const questionItem = e.target.closest('.question-item[endpoint="generate-answer"]');
    if (!questionItem) return;

    const idx = questionItem.getAttribute('data-idx');
    const detailDiv = questionItem.querySelector('.question-detail');
    const question = newsList[idx]?.title;
    const cachedAnswer = newsList[idx]?.detail; // 读取缓存

    if (!question) {
      detailDiv.textContent = "问题数据不存在，请重试";
      return;
    }

    if (detailDiv.style.display === "none") {
      // 收起其它详情
      document.querySelectorAll('.question-detail').forEach(d => {
        d.style.display = "none";
        // 重置其它箭头状态
        const otherItem = d.closest('.question-item');
        if (otherItem) otherItem.querySelector('.arrow').classList.remove('rotate');
      });
      // 显示当前详情并旋转箭头
      detailDiv.style.display = "block";
      questionItem.querySelector('.arrow').classList.add('rotate');
        // 如果有缓存直接显示，无缓存才请求
      if (cachedAnswer) {
        detailDiv.textContent = cachedAnswer;
      } else {
        detailDiv.textContent = "加载中...";
        try {
          const answer = await fetchAnswer(question);
          printText(detailDiv, answer, () => {
            newsList[idx].detail = answer; // 缓存结果
          }, 50);
        } catch (error) {
          detailDiv.textContent = "生成答案失败，请重试";
        }
      }
    } else {
      // 收起详情并重置箭头
      detailDiv.style.display = "none";
      questionItem.querySelector('.arrow').classList.remove('rotate');
    }
  });
  // 添加独立的答案获取方法
  async function fetchAnswer(question) {
    try {
      const response = await generateAnswer(question);
      return response.answer;
    } catch (error) {
      console.error('获取答案失败:', error);
      throw error; // 继续抛出错误让调用方处理
    }
  }
}

// 在DOM加载完成后添加事件监听器
document.addEventListener('DOMContentLoaded', function() {
  // 为绿色按钮添加endpoint属性
  generateBtn.setAttribute('endpoint', 'generate-questions');
  
  // 将点击事件绑定移至DOMContentLoaded内
  generateBtn.onclick = async () => {
    // 显示骨架屏和进度条
    contentArea.innerHTML = `
      <div class="progress-bar"><div class="progress-inner" id="progressInner"></div></div>
      <div class="skeleton-list">
        ${Array(10).fill('<div class="skeleton-item"></div>').join('')}
      </div>
      <div style="text-align:center;color:#aaa;margin-top:10px;">生成问题中...</div>
    `;

    // 立即启动进度条动画
    let progress = 0;
    const progressInner = document.getElementById('progressInner');
    if (!progressInner) {
      console.error('进度条元素未找到');
      return;
    }
    const timer = setInterval(() => {
      progress += Math.random() * 18 + 7;
      if (progress > 100) progress = 100;
      progressInner.style.width = progress + "%";
      if (progress >= 100) {
        clearInterval(timer);
      }
    }, 180);

    try {
      // 获取按钮的endpoint属性
      const endpoint = generateBtn.getAttribute('endpoint');
      // 调用API生成问题，传入正确参数
      const response = await generateQuestion("用户选中文本");
      // 更新新闻列表数据
      newsList = response.questions.map(question => ({
        title: question,
        detail: ""
      }));

      // API调用完成后添加平滑过渡到100%
      progressInner.style.transition = 'width 0.5s ease-in-out';
      progressInner.style.width = '100%';
      // 等待过渡完成后再执行后续操作
      setTimeout(() => {
        clearInterval(timer);
        showQuestions();
      }, 500);
    } catch (error) {
      // 错误处理
      clearInterval(timer);
      contentArea.innerHTML = `<div style="text-align:center;color:red;margin-top:40px;">生成问题失败，请重试</div>`;
    }
  };
  
  exitBtn.onclick = () => {
    contentArea.innerHTML = `<div style="text-align:center;color:#aaa;margin-top:40px;">已退出沉浸阅读模式</div>`;
  };
});

// 新闻项点击事件处理
document.querySelectorAll('.news-item').forEach((item, index) => {
    item.addEventListener('click', function() {
        const detail = this.nextElementSibling;
        const newsId = index; // 使用索引作为唯一标识
        const newsContent = newsData[index].content;

        // 检查缓存
        if (newsDetailCache[newsId]) {
            // 直接使用缓存内容
            detail.textContent = newsDetailCache[newsId];
            detail.style.display = detail.style.display === 'block' ? 'none' : 'block';
            // 旋转箭头
            // 切换旋转状态（已实现）
            this.querySelector('.arrow').classList.toggle('rotate');
            
            // 关闭其他箭头旋转状态（已实现）
            document.querySelectorAll('.arrow').forEach(arrow => {
                arrow.classList.remove('rotate');
            });
        } else {
            // 首次加载，使用打印机动效
            if (detail.style.display === 'none' || !detail.style.display) {
                // 隐藏其他详情
                document.querySelectorAll('.question-detail').forEach(d => {
                    d.style.display = 'none';
                });
                // 显示当前详情
                detail.style.display = 'block';
                // 旋转箭头
                document.querySelectorAll('.arrow').forEach(arrow => {
                    arrow.classList.remove('rotate');
                });
                this.querySelector('.arrow').classList.add('rotate');
                // 调用打印机动效并缓存结果
                printText(detail, newsContent, () => {
                    // 动画完成后缓存内容
                    newsDetailCache[newsId] = newsContent;
                });
            } else {
                // 收起详情
                detail.style.display = 'none';
                // 旋转箭头
                this.querySelector('.arrow').classList.remove('rotate');
            }
        }
    });
});

// 添加打印机动效函数 (放在文件顶部或全局作用域)
function printText(element, text, callback, speed = 30) {
  let index = 0;
  element.textContent = ''; // 清空现有内容
  element.style.whiteSpace = 'pre-wrap'; // 保留换行符
  element.style.wordBreak = 'break-word'; // 自动换行

  const timer = setInterval(() => {
    if (index < text.length) {
      // 处理换行符
      if (text[index] === '\n') {
        element.innerHTML += '<br>';
      } else {
        element.textContent += text[index];
      }
      index++;
    } else {
      clearInterval(timer);
      // 动画完成后执行回调 (用于缓存结果)
      if (typeof callback === 'function') {
        callback();
      }
    }
  }, speed);
}