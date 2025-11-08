/**
 * 将AI分析结果的JSON数据格式化为Markdown
 */
export const formatAnalysisAsMarkdown = (analysisData: any): string => {
  if (!analysisData || typeof analysisData !== 'object') {
    return '';
  }

  const markdownParts: string[] = [];

  // 1. 功能要点分析
  if (analysisData.functional_points && Array.isArray(analysisData.functional_points)) {
    markdownParts.push('## 📋 功能要点分析\n');
    analysisData.functional_points.forEach((point: any, index: number) => {
      if (typeof point === 'object' && point !== null) {
        markdownParts.push(`${index + 1}. **${point.point || '未知'}**`);
        if (point.priority) {
          markdownParts.push(`   - 优先级: ${point.priority}`);
        }
        if (point.complexity) {
          markdownParts.push(`   - 复杂度: ${point.complexity}`);
        }
        if (point.risk_level) {
          markdownParts.push(`   - 风险级别: ${point.risk_level}`);
        }
        markdownParts.push('');
      }
    });
    markdownParts.push('\n');
  }

  // 2. 测试边界条件
  if (analysisData.test_boundaries && Array.isArray(analysisData.test_boundaries)) {
    markdownParts.push('## 🔲 测试边界条件\n');
    analysisData.test_boundaries.forEach((boundary: any, index: number) => {
      if (typeof boundary === 'object' && boundary !== null) {
        markdownParts.push(`${index + 1}. **${boundary.boundary || '未知'}**`);
        if (boundary.test_type) {
          markdownParts.push(`   - 测试类型: ${boundary.test_type}`);
        }
        if (boundary.priority) {
          markdownParts.push(`   - 优先级: ${boundary.priority}`);
        }
        markdownParts.push('');
      }
    });
    markdownParts.push('\n');
  }

  // 3. 潜在风险点
  if (analysisData.risk_points && Array.isArray(analysisData.risk_points)) {
    markdownParts.push('## ⚠️ 潜在风险点\n');
    analysisData.risk_points.forEach((risk: any, index: number) => {
      if (typeof risk === 'object' && risk !== null) {
        markdownParts.push(`### 风险 ${index + 1}: ${risk.risk || '未知'}\n`);
        if (risk.impact) {
          markdownParts.push(`- **影响程度**: ${risk.impact}`);
        }
        if (risk.mitigation) {
          markdownParts.push(`- **缓解措施**: ${risk.mitigation}`);
        }
        markdownParts.push('');
      }
    });
    markdownParts.push('\n');
  }

  // 4. 测试策略建议
  if (analysisData.test_strategy && typeof analysisData.test_strategy === 'object') {
    markdownParts.push('## 🎯 测试策略建议\n');
    const strategy = analysisData.test_strategy;
    
    if (strategy.overall_approach) {
      markdownParts.push(`### 整体策略\n${strategy.overall_approach}\n`);
    }
    
    if (strategy.test_levels && Array.isArray(strategy.test_levels)) {
      markdownParts.push(`### 测试层级\n- ${strategy.test_levels.join('\n- ')}\n`);
    }
    
    if (strategy.automation_scope) {
      markdownParts.push(`### 自动化范围\n${strategy.automation_scope}\n`);
    }
    
    if (strategy.tools_recommendation && Array.isArray(strategy.tools_recommendation)) {
      markdownParts.push(`### 推荐工具\n- ${strategy.tools_recommendation.join('\n- ')}\n`);
    }
    markdownParts.push('\n');
  }

  // 5. 测试优先级
  if (analysisData.test_priorities && Array.isArray(analysisData.test_priorities)) {
    markdownParts.push('## 📊 测试优先级\n');
    analysisData.test_priorities.forEach((priority: any, index: number) => {
      if (typeof priority === 'object' && priority !== null) {
        markdownParts.push(`${index + 1}. **${priority.area || '未知'}** (优先级: ${priority.priority || '未知'})`);
        if (priority.rationale) {
          markdownParts.push(`   - 理由: ${priority.rationale}`);
        }
        markdownParts.push('');
      }
    });
    markdownParts.push('\n');
  }

  // 6. 预估工作量
  if (analysisData.estimated_effort && typeof analysisData.estimated_effort === 'object') {
    markdownParts.push('## ⏱️ 预估工作量\n');
    const effort = analysisData.estimated_effort;
    
    if (effort.total_hours) {
      markdownParts.push(`**总工作量**: ${effort.total_hours} 小时\n`);
    }
    
    if (effort.breakdown && typeof effort.breakdown === 'object') {
      markdownParts.push('### 工作量分解\n');
      const breakdownMap: Record<string, string> = {
        test_planning: '测试规划',
        test_design: '测试设计',
        test_execution: '测试执行',
        automation: '自动化'
      };
      
      Object.entries(effort.breakdown).forEach(([key, value]) => {
        const keyDisplay = breakdownMap[key] || key;
        markdownParts.push(`- ${keyDisplay}: ${value} 小时`);
      });
      markdownParts.push('');
    }
    markdownParts.push('\n');
  }

  return markdownParts.join('\n');
};

/**
 * 从流式文本中提取JSON数据
 */
export const extractJsonFromStream = (streamText: string): any | null => {
  if (!streamText) {
    console.log('extractJsonFromStream: streamText为空');
    return null;
  }

  console.log('extractJsonFromStream: 开始提取，文本长度:', streamText.length);

  try {
    // 方法1: 查找 #JSON_START# 和 #JSON_END# 标记（最可靠的方法）
    const startMarker = '#JSON_START#';
    const endMarker = '#JSON_END#';
    const startIndex = streamText.indexOf(startMarker);
    const endIndex = streamText.indexOf(endMarker);
    
    console.log('查找标记 - startIndex:', startIndex, 'endIndex:', endIndex);
    
    if (startIndex >= 0 && endIndex >= 0 && endIndex > startIndex) {
      let jsonStr = streamText.substring(startIndex + startMarker.length, endIndex);
      
      // 清理可能的 data: 前缀和多余空白
      jsonStr = jsonStr.replace(/^data:/g, '').trim();
      
      // 移除可能的前缀（如 "data:" 在字符串开头）
      jsonStr = jsonStr.replace(/^data:\s*/g, '');
      
      console.log('提取的JSON字符串长度:', jsonStr.length);
      console.log('JSON字符串前200字符:', jsonStr.substring(0, 200));
      console.log('JSON字符串后200字符:', jsonStr.substring(Math.max(0, jsonStr.length - 200)));
      
      try {
        // 尝试找到完整的JSON对象（从第一个 { 到最后一个 }）
        const firstBrace = jsonStr.indexOf('{');
        const lastBrace = jsonStr.lastIndexOf('}');
        
        if (firstBrace >= 0 && lastBrace > firstBrace) {
          jsonStr = jsonStr.substring(firstBrace, lastBrace + 1);
          console.log('提取完整JSON对象，长度:', jsonStr.length);
        }
        
        const jsonData = JSON.parse(jsonStr);
        console.log('JSON解析成功，顶层键:', Object.keys(jsonData));
        
        // 提取 data 字段（如果存在）
        if (jsonData && typeof jsonData === 'object' && 'data' in jsonData) {
          console.log('找到data字段，返回data内容');
          return jsonData.data;
        }
        console.log('直接返回JSON数据');
        return jsonData;
      } catch (e) {
        console.error('JSON解析失败:', e);
        console.error('JSON字符串前500字符:', jsonStr.substring(0, 500));
        console.error('JSON字符串后500字符:', jsonStr.substring(Math.max(0, jsonStr.length - 500)));
        
        // 尝试修复：使用更智能的方法提取完整JSON
        try {
          // 方法1: 从第一个 { 开始，找到匹配的最后一个 }
          let braceCount = 0;
          let jsonStart = -1;
          let jsonEnd = -1;
          
          for (let i = 0; i < jsonStr.length; i++) {
            if (jsonStr[i] === '{') {
              if (braceCount === 0) {
                jsonStart = i;
              }
              braceCount++;
            } else if (jsonStr[i] === '}') {
              braceCount--;
              if (braceCount === 0 && jsonStart >= 0) {
                jsonEnd = i;
                break;
              }
            }
          }
          
          if (jsonStart >= 0 && jsonEnd > jsonStart) {
            const fixedJson = jsonStr.substring(jsonStart, jsonEnd + 1);
            console.log('使用括号匹配提取JSON，长度:', fixedJson.length);
            const jsonData = JSON.parse(fixedJson);
            if (jsonData && typeof jsonData === 'object' && 'data' in jsonData) {
              console.log('修复成功，返回data字段');
              return jsonData.data;
            }
            return jsonData;
          }
          
          // 方法2: 使用正则表达式（作为备用）
          const jsonMatch = jsonStr.match(/\{[\s\S]*\}/);
          if (jsonMatch) {
            const fixedJson = jsonMatch[0];
            console.log('使用正则表达式提取JSON，长度:', fixedJson.length);
            const jsonData = JSON.parse(fixedJson);
            if (jsonData && typeof jsonData === 'object' && 'data' in jsonData) {
              return jsonData.data;
            }
            return jsonData;
          }
        } catch (e2) {
          console.error('修复JSON也失败:', e2);
        }
      }
    } else {
      console.warn('未找到完整的JSON标记');
    }

    // 方法2: 查找 ```json 代码块
    const jsonBlockMatch = streamText.match(/```json\s*([\s\S]*?)```/);
    if (jsonBlockMatch) {
      try {
        let jsonStr = jsonBlockMatch[1].trim();
        jsonStr = jsonStr.replace(/^data:/g, '').trim();
        const jsonData = JSON.parse(jsonStr);
        if (jsonData && typeof jsonData === 'object' && 'data' in jsonData) {
          return jsonData.data;
        }
        return jsonData;
      } catch (e) {
        console.warn('从代码块解析JSON失败:', e);
      }
    }

    // 方法3: 尝试直接查找完整的JSON对象（从最后一个 { 开始）
    const lastBraceIndex = streamText.lastIndexOf('{');
    if (lastBraceIndex >= 0) {
      try {
        // 从最后一个 { 开始，尝试找到匹配的 }
        let braceCount = 0;
        let jsonEnd = lastBraceIndex;
        for (let i = lastBraceIndex; i < streamText.length; i++) {
          if (streamText[i] === '{') braceCount++;
          if (streamText[i] === '}') braceCount--;
          if (braceCount === 0) {
            jsonEnd = i + 1;
            break;
          }
        }
        
        let jsonStr = streamText.substring(lastBraceIndex, jsonEnd);
        jsonStr = jsonStr.replace(/^data:/g, '').trim();
        
        const jsonData = JSON.parse(jsonStr);
        if (jsonData && typeof jsonData === 'object') {
          if ('data' in jsonData) {
            return jsonData.data;
          }
          // 如果直接包含 functional_points 等字段，说明已经是 data 部分
          if ('functional_points' in jsonData || 'test_boundaries' in jsonData) {
            return jsonData;
          }
        }
        return jsonData;
      } catch (e) {
        console.warn('直接解析JSON失败:', e);
      }
    }

    // 方法4: 尝试查找包含 "functional_points" 的JSON对象
    const functionalPointsMatch = streamText.match(/\{[\s\S]*?"functional_points"[\s\S]*?\}/);
    if (functionalPointsMatch) {
      try {
        let jsonStr = functionalPointsMatch[0];
        jsonStr = jsonStr.replace(/^data:/g, '').trim();
        const jsonData = JSON.parse(jsonStr);
        if (jsonData && typeof jsonData === 'object' && 'data' in jsonData) {
          return jsonData.data;
        }
        return jsonData;
      } catch (e) {
        console.warn('从functional_points匹配解析JSON失败:', e);
      }
    }

    return null;
  } catch (e) {
    console.error('提取JSON失败:', e);
    return null;
  }
};

