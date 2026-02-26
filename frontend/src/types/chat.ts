export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  tools_used?: string[];
  thoughts?: string;
  created_at: string;
}

export interface ToolCall {
  name: string;
  args: Record<string, unknown>;
}

export interface ToolResult {
  tool_name: string;
  tool_args: Record<string, unknown>;
  result: string;
}

export interface ChatSession {
  id: string;
  title: string | null;
  summary: string | null;
  message_count: number;
  created_at: string;
  updated_at: string;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  images?: string[];
  user_location?: string;
  display_message?: string; // Clean text for DB/history (no SYS_FILE blocks)
}

export interface ChatResponse {
  response: string;
  session_id: string;
  tool_results: ToolResult[];
  tools_used?: string[];
  thoughts?: string;
}
