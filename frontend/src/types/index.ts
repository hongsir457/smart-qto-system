export interface User {
    id: number;
    email: string;
    is_active: boolean;
}

// 定义统一的构件类型
export interface ComponentItem {
    key: string;
    component_id: string;
    component_type: string;
    dimensions: string;
    material: string;
    quantity?: number;
    unit?: string;
    volume?: number | string;
    area?: number | string;
    rebar_weight?: number;
    structural_role?: string;
    connections?: string;
    location?: string;
    confidence?: string;
    source_slice?: string;
}

// 定义统一的工程量清单显示类型
export interface QuantityListDisplay {
    success: boolean;
    components: ComponentItem[];
    summary: {
        total_components: number;
        component_types?: number;
        total_volume?: string;
        total_area?: string;
        total_concrete_volume?: number;
        total_rebar_weight?: number;
        total_formwork_area?: number;
        component_breakdown?: any;
        analysis_source?: string;
    };
    table_columns: Array<{
        title: string;
        dataIndex: string;
        key: string;
        width?: number;
    }>;
}

export interface Drawing {
    id: number;
    filename: string;
    file_path: string;
    file_type: string;
    status: string;
    label?: string;
    file_size?: number;
    ocr_results?: any;
    
    // 双轨协同分别保存的两个输出点（独立字段）
    ocr_recognition_display?: {
        drawing_basic_info: {
            drawing_title?: string;
            drawing_number?: string;
            scale?: string;
            project_name?: string;
            drawing_type?: string;
        };
        component_overview: {
            component_ids: string[];
            component_types: string[];
            material_grades: string[];
            axis_lines?: string[];
            summary: {
                total_components?: number;
                main_structure_type?: string;
                complexity_level?: string;
            };
        };
        ocr_source_info?: {
            total_slices: number;
            ocr_text_count: number;
            analysis_method: string;
        };
    };
    
    quantity_list_display?: QuantityListDisplay;
    
    recognition_results?: {
        recognition: any;
        // 新增工程量清单显示数据（输出点2）- 保留兼容性
        quantity_list_display?: QuantityListDisplay;
        // OCR识别块（输出点1）- 保留兼容性
        ocr_recognition_display?: {
            drawing_basic_info: {
                drawing_title?: string;
                drawing_number?: string;
                scale?: string;
                project_name?: string;
                drawing_type?: string;
            };
            component_overview: {
                component_ids: string[];
                component_types: string[];
                material_grades: string[];
                summary: {
                    total_components?: number;
                    main_structure_type?: string;
                    complexity_level?: string;
                };
            };
        };
        quantities?: any;
        components?: any[];
    };
    
    processing_result?: any;
    components_count?: number;
    task_id?: string;
    created_at?: string;
    updated_at?: string;
    user_id: number;
}

export interface LoginForm {
    email: string;
    password: string;
} 