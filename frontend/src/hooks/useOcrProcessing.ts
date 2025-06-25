import { useState, useCallback } from 'react';
import { message } from 'antd';
import { 
    extractRealOcrData, 
    extractComponentsData,
    createTxtDisplayResult, 
    createBasicRealDataResult, 
    createFallbackResult,
    createCompleteOcrResult,
    createSimpleOcrResult,
    normalizeOcrData,
    RealOcrData 
} from '../utils/drawingUtils';

export const useOcrProcessing = () => {
    const [ocrResult, setOcrResult] = useState<any>(null);
    const [readableOcrResults, setReadableOcrResults] = useState<any>(null);
    const [isOcrProcessing, setIsOcrProcessing] = useState(false);

    /**
     * 处理OCR数据
     */
    const processOcrData = useCallback(async (drawingData: any, id: string | string[]) => {
        console.log('🔍 [processOcrData] 开始处理OCR数据:', drawingData);
        
        try {
            const realOcrData = extractRealOcrData(drawingData);
            const componentsData = extractComponentsData(drawingData);
            console.log('🔍 [processOcrData] extractRealOcrData结果:', realOcrData);
            console.log('🔍 [processOcrData] extractComponentsData结果:', componentsData);
            
            if (realOcrData) {
                console.log('✅ [processOcrData] 找到OCR结果，开始处理:', realOcrData);
                setOcrResult(realOcrData);
                setIsOcrProcessing(false);
                
                if (realOcrData.source === 'recognition_results') {
                    console.log('🔄 [processOcrData] 处理recognition_results数据');
                    await handleRecognitionResults(drawingData, realOcrData, id, componentsData);
                } else {
                    console.log('🔄 [processOcrData] 处理传统OCR数据');
                    try {
                        await processReadableResults(realOcrData);
                    } catch (error) {
                        console.warn('⚠️ [processOcrData] 可读化处理失败，使用原始OCR数据:', error);
                        const basicOcrResult = createBasicOcrResult(realOcrData);
                        setReadableOcrResults(basicOcrResult);
                    }
                }
            } else {
                console.log('❌ [processOcrData] 未找到OCR结果，图纸状态:', drawingData.status);
                setIsOcrProcessing(false);
            }
        } catch (error) {
            console.error('❌ [processOcrData] 处理OCR数据失败:', error);
            setIsOcrProcessing(false);
            message.error('处理OCR数据失败');
        }
    }, []);

    /**
     * 处理recognition_results数据
     */
    const handleRecognitionResults = useCallback(async (
        drawingData: any, 
        realOcrData: RealOcrData, 
        id: string | string[],
        componentsData: Array<{ id: string; type: string; dimensions?: string; material?: string; quantity?: number; unit?: string; }>
    ) => {
        console.log('🔍 [handleRecognitionResults] 开始处理 recognition_results');
        
        // 检查是否存在S3 URL，以决定是否走云端数据流
        const processingResult = drawingData.processing_result ? (typeof drawingData.processing_result === 'string' ? JSON.parse(drawingData.processing_result) : drawingData.processing_result) : null;
        const s3UrlAvailable = processingResult?.result_c_human_readable?.s3_url || processingResult?.human_readable_txt?.s3_url;

        if (s3UrlAvailable) {
            console.log('✅ [handleRecognitionResults] 发现S3 URL，将尝试云端数据流处理');
            // ... (保留现有的S3处理逻辑)
            const resultBStructured = processingResult?.result_b_corrected_json;
            const resultCReadable = processingResult?.result_c_human_readable;
            const humanReadableTxt = processingResult?.human_readable_txt;
            
            if (resultCReadable && resultBStructured) {
                await handleStructuredOcrResults(resultBStructured, resultCReadable, realOcrData, id, componentsData);
            } else if (humanReadableTxt) {
                await handleHumanReadableTxt(humanReadableTxt, realOcrData, id, componentsData);
            }
        } else {
            console.log('🎨 [handleRecognitionResults] 未发现S3 URL，将使用本地 `recognition_results` 直接渲染');
            // 当没有S3 URL时，直接使用 recognition_results 中的数据创建丰富的结果
            try {
                const recResults = drawingData.recognition_results || {};
                const summary = recResults.analysis_summary || {};
                
                const richResult = {
                    meta: {
                        result_id: `local_${Date.now()}`,
                        process_time: new Date().toISOString(),
                        stage: '本地AI分析结果',
                        system_version: 'v2.0',
                        source: `图纸ID_${id}_本地`,
                        processor: recResults.analysis_engine || 'N/A'
                    },
                    readable_summary: summary.data_integrity || `本地分析完成：提取了 ${componentsData.length} 个构件。`,
                    // 创建一个简单的可读文本报告
                    readable_text: `## OCR识别结果报告\n\n- **分析引擎**: ${recResults.analysis_engine || 'N/A'}\n- **构件数量**: ${componentsData.length}\n- **文本总数**: ${recResults.total_texts || 'N/A'}`,
                    components: componentsData, // 使用已提取的构件数据
                    ocr_texts: [], // 本地数据流暂时没有原始文本
                    analysis_summary: recResults.analysis_summary,
                    analysis_engine: recResults.analysis_engine,
                    pipeline_type: recResults.pipeline_type,
                    processing_time: recResults.total_processing_time || 'N/A'
                };
                
                setReadableOcrResults(richResult);
                console.log('✅ [handleRecognitionResults] 已使用本地数据成功创建并设置显示结果');
                
            } catch (error) {
                console.error('❌ [handleRecognitionResults] 本地结果渲染失败:', error);
                const fallbackResult = createFallbackResult(realOcrData, id, error);
                fallbackResult.components = componentsData;
                setReadableOcrResults(fallbackResult);
            }
        }
    }, []);

    /**
     * 处理A→B→C完整数据流结果
     */
    const handleStructuredOcrResults = useCallback(async (
        resultBStructured: any,
        resultCReadable: any,
        realOcrData: RealOcrData,
        id: string | string[],
        componentsData: Array<{
            id: string;
            type: string;
            dimensions?: string;
            material?: string;
            quantity?: number;
            unit?: string;
        }>
    ) => {
        console.log('🔍 [handleStructuredOcrResults] 开始处理A→B→C完整数据流');
        console.log('🔍 [handleStructuredOcrResults] 使用后端代理访问S3内容');
        
        try {
            // 通过后端代理获取结果B（结构化JSON）和结果C（可读文本）
            const token = localStorage.getItem('token');
            if (!token) {
                throw new Error('未找到认证token');
            }
            
            const [structuredResponse, readableResponse] = await Promise.all([
                fetch(`/api/v1/drawings/${id}/s3-content/result_b`, {
                    headers: { Authorization: `Bearer ${token}` }
                }),
                fetch(`/api/v1/drawings/${id}/s3-content/result_c`, {
                    headers: { Authorization: `Bearer ${token}` }
                })
            ]);
            
            console.log('🔍 [handleStructuredOcrResults] 代理响应状态 - 结构化:', structuredResponse.status, '可读文本:', readableResponse.status);
            
            if (structuredResponse.ok && readableResponse.ok) {
                try {
                    const structuredData = await structuredResponse.json();
                    const readableText = await readableResponse.text();
                    
                    console.log('✅ [handleStructuredOcrResults] 成功获取代理数据:');
                    console.log('✅ [handleStructuredOcrResults] 结构化数据长度:', JSON.stringify(structuredData).length, '字符');
                    console.log('✅ [handleStructuredOcrResults] 可读文本长度:', readableText.length, '字符');
                    
                    // 安全地创建完整的显示结果，包含构件数据
                    const completeDisplayResult = createCompleteOcrResult(
                        structuredData, 
                        readableText, 
                        resultBStructured, 
                        resultCReadable, 
                        realOcrData, 
                        id,
                        componentsData
                    );
                    
                    console.log('✅ [handleStructuredOcrResults] 创建完整显示结果成功');
                    setReadableOcrResults(completeDisplayResult);
                    console.log('✅ [handleStructuredOcrResults] A→B→C结果已设置到state');
                    message.success('OCR结构化数据加载成功');
                } catch (parseError) {
                    console.error('❌ [handleStructuredOcrResults] 数据解析失败:', parseError);
                    const errorMessage = parseError instanceof Error ? parseError.message : String(parseError);
                    throw new Error(`数据解析失败: ${errorMessage}`);
                }
            } else {
                const errorMsg = `获取代理数据失败: 结构化${structuredResponse.status}(${structuredResponse.statusText}), 可读文本${readableResponse.status}(${readableResponse.statusText})`;
                throw new Error(errorMsg);
            }
        } catch (error) {
            console.error('❌ [handleStructuredOcrResults] 处理失败:', error);
            
            // 显示友好的错误信息
            const errorMessage = error instanceof Error ? error.message : String(error);
            if (errorMessage.includes('502') || errorMessage.includes('Bad Gateway')) {
                message.warning('S3存储服务暂时不可用，显示基本信息');
            } else if (errorMessage.includes('网络错误')) {
                message.warning('网络连接失败，显示基本信息');
            } else {
                message.warning('获取详细结果失败，显示基本信息');
            }
            
            // 安全地创建基本结果，不抛出异常
            try {
                const basicResult = createBasicRealDataResult(realOcrData, id);
                // 添加构件数据到基本结果
                basicResult.components = componentsData;
                setReadableOcrResults(basicResult);
            } catch (fallbackError) {
                console.error('❌ [handleStructuredOcrResults] 连基本结果都创建失败:', fallbackError);
                // 创建最简单的兜底结果
                setReadableOcrResults({
                    meta: { result_id: `error_${Date.now()}`, stage: '错误兜底显示' },
                    readable_summary: '数据加载失败，请稍后重试',
                    readable_text: `错误信息: ${errorMessage}`,
                    components: componentsData
                });
            }
        }
    }, []);

    /**
     * 处理人类可读TXT结果
     */
    const handleHumanReadableTxt = useCallback(async (
        humanReadableTxt: any, 
        realOcrData: RealOcrData, 
        id: string | string[],
        componentsData: Array<{
            id: string;
            type: string;
            dimensions?: string;
            material?: string;
            quantity?: number;
            unit?: string;
        }>
    ) => {
        console.log('🔍 [handleHumanReadableTxt] 开始处理人类可读TXT');
        console.log('🔍 [handleHumanReadableTxt] 使用后端代理访问');
        
        try {
            const token = localStorage.getItem('token');
            const response = await fetch(`/api/v1/drawings/${id}/s3-content/result_c`, {
                headers: { Authorization: `Bearer ${token}` }
            });
            console.log('🔍 [handleHumanReadableTxt] 代理响应状态:', response.status);
            
            if (response.ok) {
                const txtContent = await response.text();
                console.log('✅ [handleHumanReadableTxt] 成功获取代理TXT内容:', txtContent.length, '字符');
                console.log('✅ [handleHumanReadableTxt] TXT内容预览:', txtContent.substring(0, 200));
                
                const txtDisplayResult = createTxtDisplayResult(humanReadableTxt, realOcrData, txtContent, id);
                // 添加构件数据
                txtDisplayResult.components = componentsData;
                console.log('✅ [handleHumanReadableTxt] 创建TXT显示结果:', txtDisplayResult);
                
                setReadableOcrResults(txtDisplayResult);
                console.log('✅ [handleHumanReadableTxt] TXT结果已设置到state');
            } else {
                throw new Error(`获取TXT内容失败: ${response.status}`);
            }
        } catch (error) {
            console.error('❌ [handleHumanReadableTxt] 代理获取失败:', error);
            message.warning('获取TXT内容失败，显示基本信息');
            
            // 不抛出异常，而是显示基本结果
            const basicResult = createBasicRealDataResult(realOcrData, id);
            // 添加构件数据
            basicResult.components = componentsData;
            setReadableOcrResults(basicResult);
        }
    }, []);

    /**
     * 处理真实可读化结果
     */
    const handleRealReadableResult = useCallback(async (realReadableResult: any) => {
        console.log('✅ 发现真实可读化结果S3链接:', realReadableResult.s3_url);
        
        const response = await fetch(realReadableResult.s3_url);
        if (response.ok) {
            const s3ReadableResult = await response.json();
            console.log('✅ 成功获取S3上的真实可读化结果:', s3ReadableResult);
            setReadableOcrResults(s3ReadableResult);
        } else {
            throw new Error(`S3请求失败: ${response.status}`);
        }
    }, []);

    /**
     * 处理可读化结果
     */
    const processReadableResults = useCallback(async (rawResults: any) => {
        try {
            console.log('🔄 开始处理可读化结果，原始数据:', rawResults);
            
            const token = localStorage.getItem('token');
            if (!token) {
                console.warn('⚠️ 未找到认证token，跳过可读化处理');
                message.warning('未登录，无法处理可读化结果');
                return;
            }
            
            const normalizedOcrData = normalizeOcrData(rawResults);
            
            const requestBody = {
                drawing_id: Number(window.location.pathname.split('/').pop()),
                ocr_data: normalizedOcrData
            };
            
            console.log('📤 发送请求数据:', JSON.stringify(requestBody, null, 2));
            
            const response = await fetch(`/api/v1/ocr/process-results`, {
                method: 'POST',
                headers: { 
                    Authorization: 'Bearer ' + token,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestBody)
            });
            
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            
            const result = await response.json();
            console.log('✅ 可读化处理成功:', result);
            setReadableOcrResults(result.data || result);
        } catch (error) {
            console.error('❌ 处理可读化结果失败:', error);
            throw error;
        }
    }, []);

    /**
     * 创建基本的OCR结果显示结构
     */
    const createBasicOcrResult = useCallback((rawOcrData: any) => {
        console.log('🔧 创建基本OCR结果结构:', rawOcrData);
        
        const normalizedData = normalizeOcrData(rawOcrData);
        const textRegions = normalizedData.text_regions || [];
        
        const totalTexts = textRegions.length;
        const avgConfidence = totalTexts > 0 
            ? textRegions.reduce((sum: number, item: any) => sum + (item.confidence || 0), 0) / totalTexts 
            : 0;
        
        const componentCodes: any[] = [];
        const dimensions: any[] = [];
        const otherText: any[] = [];
        
        textRegions.forEach((item: any, index: number) => {
            const text = item.text || '';
            if (/^[A-Z]{1,3}\d+$/i.test(text)) {
                componentCodes.push({ text, confidence: item.confidence, index });
            } else if (/^\d+[×*xX]\d+$/.test(text)) {
                dimensions.push({ text, confidence: item.confidence, index });
            } else {
                otherText.push({ text, confidence: item.confidence, index });
            }
        });
        
        return {
            meta: {
                result_id: `basic_${Date.now()}`,
                process_time: new Date().toISOString(),
                stage: '基本OCR结果显示',
                system_version: 'v1.0',
                source: `图纸基本显示`,
                processor: 'BasicOCRDisplay'
            },
            raw_statistics: {
                total_texts: totalTexts,
                total_polygons: 0,
                has_scores: true,
                has_text_polygons: false,
                average_confidence: avgConfidence
            },
            classified_content: {
                project_info: [],
                drawing_info: [],
                component_codes: componentCodes,
                dimensions: dimensions,
                materials: [],
                elevations: [],
                personnel: [],
                dates: [],
                specifications: [],
                other_text: otherText
            },
            project_analysis: { status: '基本显示模式' },
            drawing_analysis: { status: '基本显示模式' },
            component_analysis: {
                total_components: componentCodes.length,
                total_dimensions: dimensions.length,
                component_types: {},
                dimension_patterns: dimensions.map(d => d.text)
            },
            construction_specs: [],
            readable_summary: `基本OCR结果: 识别到 ${totalTexts} 个文本项，包含 ${componentCodes.length} 个构件编号，${dimensions.length} 个尺寸`,
            readable_text: textRegions.map((item: any, index: number) => 
                `[${index + 1}] ${item.text} (置信度: ${(item.confidence * 100).toFixed(1)}%)`
            ).join('\n'),
            sealos_storage: { saved: false, error: '基本显示模式' }
        };
    }, []);

    /**
     * 处理自动OCR
     */
    const handleAutoOCR = useCallback(async (drawingId: number) => {
        if (isOcrProcessing) return;
        
        setIsOcrProcessing(true);
        
        try {
            const token = localStorage.getItem('token');
            if (!token) {
                message.error('请先登录');
                return;
            }
            
            const response = await fetch(`/api/v1/drawings/${drawingId}/ocr`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`OCR处理失败: ${response.status}`);
            }
            
            const result = await response.json();
            
            if (result.task_id) {
                message.success('OCR识别任务已启动');
            }
        } catch (error) {
            console.error('自动OCR失败:', error);
            message.error('自动OCR失败，请稍后重试');
        } finally {
            setIsOcrProcessing(false);
        }
    }, [isOcrProcessing]);

    return {
        ocrResult,
        readableOcrResults,
        isOcrProcessing,
        setIsOcrProcessing,
        processOcrData,
        handleAutoOCR
    };
}; 