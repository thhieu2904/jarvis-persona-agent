import api from "./api";

export interface Task {
  id: string;
  title: string;
  description: string;
  due_date: string | null;
  status: string;
  priority: string;
  is_pinned: boolean;
}

export const tasksService = {
  async listTasks(status = "pending"): Promise<Task[]> {
    const res = await api.get<{ data: Task[] }>(`/tasks/?status=${status}`);
    return res.data.data;
  },

  async updateTask(
    id: string,
    data: Partial<
      Pick<
        Task,
        | "title"
        | "description"
        | "due_date"
        | "priority"
        | "status"
        | "is_pinned"
      >
    >,
  ): Promise<Task> {
    const res = await api.put<{ data: Task }>(`/tasks/${id}`, data);
    return res.data.data;
  },

  async deleteTask(id: string): Promise<void> {
    await api.delete(`/tasks/${id}`);
  },
};
