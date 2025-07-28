import { getOptions } from '@/lib/storage';
import Turndown from 'turndown';
import { Readability } from '@mozilla/readability';
import Defuddle from 'defuddle';
import { defaultTagsToRemove } from '@/lib/tagsToRemove';
import { browser } from 'wxt/browser';

/**
 * 计算两个字符串的相似度
 * @param s1 第一个字符串
 * @param s2 第二个字符串
 * @returns 相似度分数(0-1之间)
 */
export function similarity(s1: string, s2: string): number {
    let longer: string = s1;
    let shorter: string = s2;
    
    if (s1.length < s2.length) {
        longer = s2;
        shorter = s1;
    }
    
    const longerLength: number = longer.length;
    if (longerLength === 0) {
        return 1.0;
    }
    
    return (longerLength - editDistance(longer, shorter)) / parseFloat(longerLength.toString());
}

/**
 * 计算两个字符串的编辑距离(Levenshtein距离)
 * @param s1 第一个字符串
 * @param s2 第二个字符串
 * @returns 编辑距离数值
 */
export function editDistance(s1: string, s2: string): number {
    s1 = s1.toLowerCase();
    s2 = s2.toLowerCase();

    const costs: number[] = [];
    for (let i = 0; i <= s1.length; i++) {
        let lastValue: number = i;
        for (let j = 0; j <= s2.length; j++) {
            if (i === 0) {
                costs[j] = j;
            } else {
                if (j > 0) {
                    let newValue: number = costs[j - 1];
                    if (s1.charAt(i - 1) !== s2.charAt(j - 1)) {
                        newValue = Math.min(Math.min(newValue, lastValue), costs[j]) + 1;
                    }
                    costs[j - 1] = lastValue;
                    lastValue = newValue;
                }
            }
        }
        if (i > 0) {
            if (s2.length < costs.length) {
                costs[s2.length] = lastValue;
            } else {
                costs.push(lastValue);
            }
        }
    }
    return costs[s2.length];
}

/**
 * 将当前页面内容转换为Markdown格式
 * @returns 转换后的Markdown字符串
 */
export async function convertToMarkdown(htmlContent: string): Promise<string> {
  try {
    const [activeTab] = await browser.tabs.query({
      active: true,
      currentWindow: true,
    });
    if (!activeTab.id) {
      console.error('Active tab has no ID');
      return '';
    }

    const results = await browser.scripting.executeScript({
      target: { tabId: activeTab.id },
      func: () => document.body.outerHTML,
    });

    if (!results || results.length === 0 || !results[0].result) {
      console.error('No content found in active tab');
      return '';
    }

    const bodyContent = results[0].result;
    const options = await getOptions();
    const { useReadability, useDeffudle } = options;

    let markdown = bodyContent;

    if (useReadability) {
      const doc = new DOMParser().parseFromString(bodyContent, 'text/html');
      doc.getElementById('cpdown-notification')?.remove();

      const article = new Readability(doc).parse();
      if (!article?.content) return '';

      markdown = new Turndown({})
        .remove(defaultTagsToRemove)
        .turndown(article.content);
    } else if (useDeffudle) {
      try {
        const doc = new DOMParser().parseFromString(bodyContent, 'text/html');
        doc.getElementById('cpdown-notification')?.remove();
        const defuddle = new Defuddle(doc, {
          debug: true,
          markdown: true,
          separateMarkdown: false,
        }).parse();
        markdown = new Turndown({})
          .remove(defaultTagsToRemove)
          .turndown(defuddle.content);
      } catch (error) {
        console.error('Error processing with Defuddle:', error);
        // 降级处理
        markdown = new Turndown({})
          .remove(defaultTagsToRemove)
          .turndown(bodyContent);
      }
    } else {
      markdown = new Turndown({})
        .remove(defaultTagsToRemove)
        .turndown(bodyContent);
    }

    return markdown;
  } catch (error) {
    console.error('Error converting to markdown:', error);
    return '';
  }
};

/**
 * 获取当前标签页的内容
 */
export const getCurrentTabContent = async (): Promise<string> => {
  try {
    // 使用浏览器API获取当前标签页
    const [tab] = await browser.tabs.query({ active: true, currentWindow: true });
    
    // 检查是否为about:blank页面
    if (tab.url === 'about:blank') {
      console.log('当前为空白页面，不执行内容提取');
      return '';
    }
    
    if (!tab.id) {
      console.log('无法获取当前标签页ID');
      return '';
    }

    // 注入脚本获取页面内容
    const result = await browser.scripting.executeScript({
      target: { tabId: tab.id! },
      func: () => {
        // 获取页面主要内容（可根据需要调整选择器）
        const mainContent = document.querySelector('main') || document.body;
        return mainContent?.innerText || document.body.innerText;
      }
    });

    return result[0].result ?? '';
  } catch (error) {
    console.error('获取页面内容时出错:', error);
    return '';
  }
};