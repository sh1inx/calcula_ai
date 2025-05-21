import { ApiResponseInterface } from "@/interfaces/backend.response.interface";

export default class ApiService {
    async post<T extends ApiResponseInterface>(endpoint: string, data: any): Promise<T> {
        const requestOptions = {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        };
    
        try {
            let response = await fetch(endpoint, requestOptions);
      
            if (!response.ok) {
                console.log("Erro na resposta da API");
                const errorResponse = await response.json();
                return errorResponse;
            }

            return await response.json()
            
      
        } catch (error) {
            throw error;
        }
    }

    async get<T extends ApiResponseInterface>(endpoint: string, params?: Record<string, string | number>): Promise<T> {
        const queryString = params ? '?' + new URLSearchParams(params as any).toString() : '';
        const url = `${endpoint}${queryString}`;
        const requestOptions = {
            method: 'GET',
            headers: { 
                'Content-Type': 'application/json'
            } 
        }
        
        try {
            let response = await fetch(url, requestOptions);

            if (!response.ok) {
                console.log("Erro na resposta da API");
                const errorResponse = await response.json();
                console.log("Resposta de erro:", errorResponse);
                throw new Error(errorResponse.response?.msg || "Erro desconhecido na requisição.");
            }

            return await response.json();
        } catch (error) {
            throw error;
        }
    }

    async put<T extends ApiResponseInterface>(endpoint: string, data: any): Promise<T> {
        const requestOptions = {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        };
    
        try {
            let response = await fetch(endpoint, requestOptions);
      
            if (!response.ok) {
                console.log("Erro na resposta da API");
                const errorResponse = await response.json();
                return errorResponse;
            }

            return await response.json()
            
      
        } catch (error) {
            throw error;
        }
    }

    async postFormData<T extends ApiResponseInterface>(endpoint: string, data: any): Promise<T> {
        const requestOptions = {
            method: 'POST',
            headers: {
                "Content-Type": "multipart/form-data",
            },
            body: data
        };
    
        try {
            let response = await fetch(endpoint, requestOptions);
      
            if (!response.ok) {
                let errorResponse = await response.json();
                throw new Error(errorResponse.response?.msg || "Erro desconhecido na requisição.");
            }
      
            return await response.json();
        } catch (error) {
            throw error;
        }
    }
}