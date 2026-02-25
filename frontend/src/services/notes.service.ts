import api from "./api";

export interface Note {
  id: string;
  content: string;
  note_type: string;
  tags: string[];
  url: string | null;
  related_subject: string | null;
  is_pinned: boolean;
  created_at: string;
}

export const notesService = {
  async listNotes(): Promise<Note[]> {
    // Only fetch unarchived notes for the widget
    const res = await api.get<{ data: Note[] }>(
      "/notes/?include_archived=false",
    );
    return res.data.data;
  },

  async createNote(data: {
    content: string;
    note_type?: string;
    tags?: string[];
  }): Promise<Note> {
    const res = await api.post<{ data: Note }>("/notes/", data);
    return res.data.data;
  },

  async updateNote(
    id: string,
    data: Partial<
      Pick<
        Note,
        | "content"
        | "note_type"
        | "tags"
        | "url"
        | "related_subject"
        | "is_pinned"
      >
    >,
  ): Promise<Note> {
    const res = await api.put<{ data: Note }>(`/notes/${id}`, data);
    return res.data.data;
  },

  async deleteNote(id: string): Promise<void> {
    await api.delete(`/notes/${id}`);
  },
};
