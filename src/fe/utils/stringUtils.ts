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
 * 生成用户ID，格式为：最新时间戳+0-9随机数
 * @returns 生成的用户ID字符串
 */
export function generateUserId(): string {
    // 获取当前时间戳
    const timestamp = Date.now().toString();
    // 生成0-9之间的随机数
    const randomNum = Math.floor(Math.random() * 10).toString();
    // 组合时间戳和随机数
    return timestamp + randomNum;
}
/**
 * 对字符串进行SHA256哈希处理
 * @param str 要哈希的字符串
 * @returns 哈希后的十六进制字符串
 */
export async function sha256(str: string): Promise<string> {
  const encoder = new TextEncoder();
  const data = encoder.encode(str);
  const hash = await crypto.subtle.digest('SHA-256', data);
  return Array.from(new Uint8Array(hash))
    .map(byte => byte.toString(16).padStart(2, '0'))
    .join('');
}