import { useState, useEffect, useRef } from "react";
import {
  BookOpen,
  Upload,
  Trash2,
  Download,
  FileText,
  X,
  CheckCircle2,
  AlertCircle,
  Loader2,
} from "lucide-react";
import {
  knowledgeService,
  type StudyMaterial,
} from "../../services/knowledge.service";
import styles from "./KnowledgeBasePage.module.css";

export default function KnowledgeBasePage() {
  const [documents, setDocuments] = useState<StudyMaterial[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Modal state
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<
    "study" | "work" | "personal" | "other"
  >("study");
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadError, setUploadError] = useState<string | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const data = await knowledgeService.getDocuments();
      setDocuments(data || []);
      setError(null);
    } catch (err: any) {
      console.error("Failed to fetch documents:", err);
      setError("Không thể tải danh sách tài liệu. Vui lòng thử lại sau.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
    // Auto-refresh periodically if there are documents in "processing" state
    const interval = setInterval(() => {
      setDocuments((prevDocs) => {
        const hasProcessing = prevDocs.some(
          (d) => d.processing_status === "processing",
        );
        if (hasProcessing) {
          fetchDocuments();
        }
        return prevDocs;
      });
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const handleDelete = async (id: string) => {
    if (
      !window.confirm(
        "Bác có chắc muốn xóa tài liệu này không? AI sẽ quên những kiến thức trong file này đấy.",
      )
    ) {
      return;
    }

    try {
      await knowledgeService.deleteDocument(id);
      setDocuments((docs) => docs.filter((d) => d.id !== id));
    } catch (err) {
      console.error("Error deleting document:", err);
      alert("Xóa tài liệu thất bại.");
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      // Validate file type
      const validExts = [".pdf", ".docx", ".txt", ".md"];

      const isExtValid = validExts.some((ext) =>
        file.name.toLowerCase().endsWith(ext),
      );

      if (!isExtValid) {
        setUploadError("Chỉ hỗ trợ file PDF, DOCX, TXT và MD.");
        return;
      }

      if (file.size > 50 * 1024 * 1024) {
        setUploadError("Dung lượng file vượt quá 50MB.");
        return;
      }

      setSelectedFile(file);
      setUploadError(null);
    }
  };

  const clearModal = () => {
    setSelectedFile(null);
    setSelectedDomain("study");
    setUploadError(null);
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = "";
  };

  const handleCloseModal = () => {
    if (!isUploading) {
      setIsModalOpen(false);
      clearModal();
    }
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    setIsUploading(true);
    setUploadError(null);
    setUploadProgress(0);

    const formData = new FormData();
    formData.append("file", selectedFile);
    formData.append("domain", selectedDomain);

    try {
      // Simulate progress for UI since axios uploadProgress isn't perfectly reflecting backend processing
      const progressInterval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 90) return prev;
          return prev + 10;
        });
      }, 500);

      await knowledgeService.uploadDocument(selectedFile, selectedDomain);

      clearInterval(progressInterval);
      setUploadProgress(100);

      // Refresh list after brief delay
      setTimeout(() => {
        fetchDocuments();
        handleCloseModal();
        setIsUploading(false);
      }, 500);
    } catch (err: any) {
      console.error("Upload error:", err);
      setUploadError(
        err.response?.data?.detail ||
          "Đã xảy ra lỗi khi tải file. Vui lòng thử lại.",
      );
      setIsUploading(false);
      setUploadProgress(0);
    }
  };

  const getStatusDisplay = (status: string) => {
    switch (status) {
      case "success":
        return (
          <span className={`${styles.statusWrapper} ${styles.status_success}`}>
            <CheckCircle2 size={16} /> Đã học
          </span>
        );
      case "processing":
        return (
          <span
            className={`${styles.statusWrapper} ${styles.status_processing}`}
          >
            <Loader2 size={16} className={styles.spinner} /> Đang xử lý
          </span>
        );
      case "failed":
        return (
          <span className={`${styles.statusWrapper} ${styles.status_error}`}>
            <AlertCircle size={16} /> Lỗi
          </span>
        );
      default:
        return <span>{status}</span>;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return "0 Bytes";
    const k = 1024;
    const sizes = ["Bytes", "KB", "MB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + " " + sizes[i];
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div>
          <h1 className={styles.title}>Quản lý Kiến Thức (Knowledge Base)</h1>
          <p className={styles.subtitle}>
            Dạy cho AI những tài liệu, sách giáo trình chuyên môn của bạn.
          </p>
        </div>
        <button
          className={styles.uploadBtn}
          onClick={() => setIsModalOpen(true)}
        >
          <Upload size={18} />
          <span>Tải file lên</span>
        </button>
      </header>

      {error && (
        <div
          className={`${styles.statusWrapper} ${styles.status_error}`}
          style={{ marginBottom: 16 }}
        >
          {error}
        </div>
      )}

      <div className={styles.tableContainer}>
        {loading && documents.length === 0 ? (
          <div className={styles.emptyState}>
            <Loader2
              size={32}
              className={`${styles.emptyIcon} ${styles.spinner}`}
            />
            <p>Đang tải tài liệu...</p>
          </div>
        ) : documents.length === 0 ? (
          <div className={styles.emptyState}>
            <BookOpen size={48} className={styles.emptyIcon} />
            <h3>Chưa có tài liệu nào</h3>
            <p>
              Tải lên tài liệu PDF, Word, Txt để bắt đầu xây dựng não bộ cho AI.
            </p>
          </div>
        ) : (
          <table className={styles.table}>
            <thead>
              <tr>
                <th>Tên tài liệu</th>
                <th>Phân loại</th>
                <th>Trạng thái RAG</th>
                <th>Tác vụ</th>
              </tr>
            </thead>
            <tbody>
              {documents.map((doc) => (
                <tr key={doc.id}>
                  <td>
                    <div className={styles.tableNameCell}>
                      <div className={styles.fileIconWrapper}>
                        <FileText size={20} />
                      </div>
                      <span title={doc.file_name}>{doc.file_name}</span>
                    </div>
                  </td>
                  <td>
                    <span
                      className={`${styles.domainBadge} ${(styles as any)[`domain_${doc.domain}`] || styles.domain_other}`}
                    >
                      {doc.domain === "study"
                        ? "Học tập"
                        : doc.domain === "work"
                          ? "Công việc"
                          : doc.domain === "personal"
                            ? "Cá nhân"
                            : "Khác"}
                    </span>
                  </td>
                  <td>{getStatusDisplay(doc.processing_status)}</td>
                  <td>
                    <div className={styles.actionCell}>
                      {doc.download_url && (
                        <a
                          href={doc.download_url}
                          target="_blank"
                          rel="noreferrer"
                          className={styles.downloadLink}
                          title="Tải xuống tài liệu gốc"
                        >
                          <Download size={18} />
                        </a>
                      )}
                      <button
                        className={styles.deleteBtn}
                        onClick={() => handleDelete(doc.id)}
                        title="Xóa tài liệu này khỏi bộ nhớ AI"
                      >
                        <Trash2 size={18} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* Upload Modal */}
      {isModalOpen && (
        <div className={styles.modalOverlay} onClick={handleCloseModal}>
          <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h2 className={styles.modalTitle}>Dạy kiến thức mới</h2>
              <button
                className={styles.closeModalBtn}
                onClick={handleCloseModal}
                disabled={isUploading}
              >
                <X size={20} />
              </button>
            </div>

            {!selectedFile ? (
              <div
                className={styles.dropZone}
                onClick={() => fileInputRef.current?.click()}
              >
                <Upload
                  size={32}
                  color="#9ca3af"
                  style={{ margin: "0 auto 12px" }}
                />
                <strong>Nhấn để chọn file tải lên</strong>
                <p className={styles.dropZoneData}>
                  Hỗ trợ: PDF, DOCX, TXT, MD (Max 50MB)
                </p>
                <input
                  type="file"
                  ref={fileInputRef}
                  onChange={handleFileChange}
                  style={{ display: "none" }}
                  accept=".pdf,.docx,.txt,.md"
                />
              </div>
            ) : (
              <div className={styles.selectedFile}>
                <FileText size={24} color="#2563eb" />
                <div className={styles.fileInfo}>
                  <div className={styles.fileName}>{selectedFile.name}</div>
                  <div className={styles.fileSize}>
                    {formatFileSize(selectedFile.size)}
                  </div>
                </div>
                {!isUploading && (
                  <button className={styles.removeFileBtn} onClick={clearModal}>
                    <X size={16} />
                  </button>
                )}
              </div>
            )}

            {uploadError && (
              <div
                className={`${styles.statusWrapper} ${styles.status_error}`}
                style={{ marginBottom: 16 }}
              >
                <AlertCircle size={16} /> {uploadError}
              </div>
            )}

            <div className={styles.formGroup}>
              <label className={styles.label}>Phân loại tài liệu:</label>
              <select
                value={selectedDomain}
                onChange={(e) => setSelectedDomain(e.target.value as any)}
                className={styles.select}
                disabled={isUploading || !selectedFile}
              >
                <option value="study">
                  🎓 Học tập (Giáo trình, Bài giảng, Đề cương)
                </option>
                <option value="work">
                  💼 Công việc (Quy trình, Tài liệu mật, Báo cáo)
                </option>
                <option value="personal">
                  🏠 Cá nhân (Sở thích, Sách Self-help, Thể thao)
                </option>
                <option value="other">📦 Khác</option>
              </select>
            </div>

            {isUploading && (
              <div className={styles.loadingContainer}>
                <div className={styles.progressBar}>
                  <div
                    className={styles.progressFill}
                    style={{ width: `${uploadProgress}%` }}
                  ></div>
                </div>
                <div className={styles.progressText}>
                  {uploadProgress === 100
                    ? "Đang xử lý Vector hoàn tất..."
                    : `Đang đẩy lên kho dữ liệu... ${uploadProgress}%`}
                </div>
              </div>
            )}

            <button
              className={styles.uploadSubmitBtn}
              onClick={handleUpload}
              disabled={!selectedFile || isUploading}
              style={{ marginTop: 24 }}
            >
              {isUploading ? (
                <>
                  <Loader2 size={18} className={styles.spinner} /> Đang xử lý...
                </>
              ) : (
                <>
                  <CheckCircle2 size={18} /> Đưa vào kho Kiến thức
                </>
              )}
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
