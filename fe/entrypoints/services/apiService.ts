import { similarity } from '@/utils/stringUtils';
// 定义响应接口
export interface GenerateQuestionResponse {
  questions: string[];
}

export interface GenerateAnswerResponse {
  answer: string;
}

// 定义API端点类型
type ApiEndpoint = 'generate-questions' | 'generate-answer';

// 定义请求数据类型
interface GenerateQuestionParams {
  text: string;
}

interface GenerateAnswerParams {
  question: string;
}

/**
 * 模拟API调用函数
 * @param endpoint 请求端点
 * @param data 请求参数
 * @returns 模拟API响应的Promise
 */
function simulateAPICall(
  endpoint: ApiEndpoint,
  data: GenerateQuestionParams | GenerateAnswerParams
): Promise<GenerateQuestionResponse | GenerateAnswerResponse> {
  return new Promise((resolve) => {
    // 模拟网络延迟
    setTimeout(() => {
      if (endpoint === 'generate-questions') {
        // 根据选中文本的内容生成模拟问题
        const sampleQuestions = [
          "这个观点的主要依据是什么？",
          "是否有相反的观点或证据？",
          "这个结论在哪些情况下可能不成立？",
          "这个观点与其他领域的知识有什么联系？",
          "如果改变某个前提条件，结论会如何变化？",
          "这个理论如何应用到现实场景中？",
          "作者的立场和背景如何影响这个观点？",
          "这个问题是否存在更深层次的原因？"
        ];
        
        // 随机选择5-7个问题
        const shuffled = [...sampleQuestions].sort(() => 0.5 - Math.random());
        resolve({
          questions: shuffled.slice(0, Math.floor(Math.random() * 3) + 5)
        });
      } else if (endpoint === 'generate-answer') {
        // 根据问题生成模拟回答
        const answers: Record<string, string> = {
        "这个观点的主要依据是什么？": "这个观点主要基于作者在过去五年中对200多个案例的研究。作者通过对比实验和数据分析发现，在85%的情况下，该现象都呈现出相同的趋势。此外，其他三位学者在相关领域的研究也支持这一结论。然而，这些研究大多集中在特定的环境下，可能存在样本偏差的问题。",
                    "是否有相反的观点或证据？": "是的，有学者提出了不同的看法。Smith(2023)在一项针对亚洲市场的研究中发现，约30%的案例显示出相反的结果。他认为原观点可能忽略了文化差异的影响。另外，Jones(2024)通过建模分析指出，当某个变量超过一定阈值时，原结论可能不再成立。",
                    "这个结论在哪些情况下可能不成立？": "这个结论的成立依赖于几个前提条件：1) 市场处于完全竞争状态；2) 信息充分透明；3) 参与者都是理性的。在现实中，如果这些条件不满足，结论可能不成立。例如，在垄断市场中，或者当参与者受到情绪影响时，结果可能大不相同。",
                    "这个观点与其他领域的知识有什么联系？": "这个观点与行为经济学中的'锚定效应'有密切联系，人们在决策时往往过于依赖最初获得的信息。此外，它也与心理学中的'确认偏差'相关，即人们倾向于寻找支持自己观点的证据。在管理学中，类似的现象被称为'路径依赖'，指组织或个人一旦选择了某种路径，就会在未来不断强化这种选择。",
                    "如果改变某个前提条件，结论会如何变化？": "如果放松'信息充分透明'这个前提条件，结论可能会发生显著变化。研究表明，当信息不对称程度增加时，市场效率会下降，原结论中的因果关系可能会被削弱。此外，如果考虑'参与者有限理性'的因素，个体的决策偏差可能会导致整体结果偏离预期。",
                    "这个理论如何应用到现实场景中？": "这个理论可以应用于多个领域：在投资决策中，投资者可以警惕过度自信的陷阱；在产品设计中，设计师可以利用这个原理提高用户体验；在团队管理中，领导者可以通过多样化团队成员的背景来减少群体思维的影响。例如，某科技公司在产品迭代过程中，通过引入外部用户反馈，成功避免了因内部过度自信导致的设计失误。",
                    "作者的立场和背景如何影响这个观点？": "作者是该领域的知名专家，长期致力于研究认知偏差对决策的影响。他的研究得到了多家科技公司的资助，这可能使他的研究更偏向于应用领域。此外，作者曾在多家互联网企业担任顾问，这种实践背景可能使他更关注理论的现实意义，但也可能导致他忽略一些理论上的细节。",
                    "这个问题是否存在更深层次的原因？": "表面上看，这个问题是由信息不对称导致的，但更深层次的原因可能涉及社会文化和制度因素。例如，某些行业的潜规则可能阻碍了信息的流通，而法律制度的不完善可能使得信息披露的成本过高。此外，认知心理学的研究表明，人类天生具有简化复杂信息的倾向，这也可能是问题产生的根本原因之一。"
        };

        // 类型守卫确保数据类型
        if ('question' in data) {
          const closestQuestion = Object.keys(answers).reduce((a, b) =>
            similarity(data.question, a) > similarity(data.question, b) ? a : b
          );
          
          resolve({
            answer: answers[closestQuestion] || "这个问题需要更深入的分析和研究..."
          });
        }
      }
    }, 800); // 模拟0.8秒的网络延迟
  });
}

/**
 * 生成问题API
 * @param text 选中文本
 * @returns 问题列表响应
 */
export function generateQuestion(
  text: string
): Promise<GenerateQuestionResponse> {
  return simulateAPICall('generate-questions', { text }) as Promise<GenerateQuestionResponse>;
}

/**
 * 生成回答API
 * @param question 问题文本
 * @returns 回答响应
 */
export function generateAnswer(
  question: string
): Promise<GenerateAnswerResponse> {
  return simulateAPICall('generate-answer', { question }) as Promise<GenerateAnswerResponse>;
}