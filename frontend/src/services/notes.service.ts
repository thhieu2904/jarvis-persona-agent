import api from "./api";

export interface Note {
  id: string;
  content: string;
  note_type: string;
  tags: string[];
  url: string | null;
  related_subject: string | null;
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
};
