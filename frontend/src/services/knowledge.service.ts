import api from "./api";

export interface StudyMaterial {
  id: string;
  file_name: string;
  domain: "study" | "work" | "personal" | "other";
  processing_status: "processing" | "success" | "failed";
  created_at: string;
  download_url?: string;
}

export const knowledgeService = {
  async getDocuments(): Promise<StudyMaterial[]> {
    const res = await api.get<{ data: StudyMaterial[] }>("/knowledge");
    return res.data.data;
  },

  async deleteDocument(id: string): Promise<void> {
    await api.delete(`/knowledge/${id}`);
  },

  async uploadDocument(
    file: File,
    domain: "study" | "work" | "personal" | "other",
  ): Promise<any> {
    const formData = new FormData();
    formData.append("file", file);
    formData.append("domain", domain);

    const res = await api.post("/knowledge/upload", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    return res.data;
  },

  async extractText(
    file: File,
  ): Promise<{
    text: string;
    metadata: { file_name: string; storage_path: string };
  }> {
    const formData = new FormData();
    formData.append("file", file);

    const res = await api.post<{
      status: string;
      message: string;
      data: { file_name: string; storage_path: string; content: string };
    }>("/knowledge/extract-text", formData, {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    });

    // Unwrap the backend envelope → return the shape ChatPage.tsx expects
    return {
      text: res.data.data.content,
      metadata: {
        file_name: res.data.data.file_name,
        storage_path: res.data.data.storage_path,
      },
    };
  },
};
