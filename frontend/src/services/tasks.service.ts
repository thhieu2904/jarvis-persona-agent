import api from "./api";

export interface Task {
  id: string;
  title: string;
  description: string;
  due_date: string | null;
  status: string;
  priority: string;
}

export const tasksService = {
  async listTasks(status = "pending"): Promise<Task[]> {
    const res = await api.get<{ data: Task[] }>(`/tasks/?status=${status}`);
    return res.data.data;
  },
};
