export interface User {
    id: number;
    email: string;
    is_active: boolean;
}

export interface Drawing {
    id: number;
    filename: string;
    file_path: string;
    file_type: string;
    status: string;
    recognition_results?: {
        recognition: any;
        quantities: {
            walls: Array<{
                id: number;
                type: string;
                material: string;
                quantities: {
                    volume: number;
                    area: number;
                    length: number;
                };
            }>;
            columns: Array<{
                id: number;
                type: string;
                material: string;
                quantities: {
                    volume: number;
                    area: number;
                    height: number;
                };
            }>;
            beams: Array<{
                id: number;
                type: string;
                material: string;
                quantities: {
                    volume: number;
                    length: number;
                    area: number;
                };
            }>;
            slabs: Array<{
                id: number;
                type: string;
                material: string;
                quantities: {
                    volume: number;
                    area: number;
                    thickness: number;
                };
            }>;
            foundations: Array<{
                id: number;
                type: string;
                material: string;
                quantities: {
                    volume: number;
                    area: number;
                    height: number;
                };
            }>;
            total: {
                wall_volume: number;
                column_volume: number;
                beam_volume: number;
                slab_volume: number;
                foundation_volume: number;
                total_volume: number;
            };
        };
    };
    created_at: string;
    updated_at: string;
    user_id: number;
}

export interface LoginForm {
    email: string;
    password: string;
} 