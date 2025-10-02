import Editor from '@monaco-editor/react';
import {
    ArrowBack as BackIcon,
    Download as DownloadIcon,
    FileDownload as ExportIcon,
    MoreVert as MoreIcon,
    Preview as PreviewIcon,
    Save as SaveIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Divider,
    FormControl,
    IconButton,
    InputLabel,
    Menu,
    MenuItem,
    Paper,
    Select,
    TextField,
    Toolbar,
    Typography
} from '@mui/material';
import React, { useCallback, useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';

interface Document {
  title: string;
  content: string;
  format: string;
  template_used?: string;
  created_at?: string;
}

interface ExportFormat {
  format: string;
  name: string;
  description: string;
}

const EditorView: React.FC = () => {
  const location = useLocation();
  const navigate = useNavigate();

  // Document state
  const [document, setDocument] = useState<Document | null>(null);
  const [content, setContent] = useState<string>('');
  const [title, setTitle] = useState<string>('');
  const [hasChanges, setHasChanges] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');

  // Export functionality
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [exportFormat, setExportFormat] = useState<string>('pdf');
  const [exportFormats, setExportFormats] = useState<ExportFormat[]>([]);
  const [exporting, setExporting] = useState(false);

  // Menu state
  const [menuAnchor, setMenuAnchor] = useState<null | HTMLElement>(null);

  // Preview state
  const [previewDialogOpen, setPreviewDialogOpen] = useState(false);
  const [previewContent, setPreviewContent] = useState<string>('');

  useEffect(() => {
    // Load document from navigation state or create new
    const docFromState = location.state?.document;
    if (docFromState) {
      setDocument(docFromState);
      setContent(docFromState.content);
      setTitle(docFromState.title);
    }

    // Load export formats
    loadExportFormats();
  }, [location.state]);

  const loadExportFormats = async () => {
    try {
      const response = await apiService.get('/api/user-documents/supported-formats');
      setExportFormats(response.export_formats || []);
    } catch (error) {
      console.error('Error loading export formats:', error);
    }
  };

  const handleContentChange = useCallback((value: string | undefined) => {
    const newContent = value || '';
    setContent(newContent);
    setHasChanges(newContent !== document?.content);
  }, [document?.content]);

  const handleTitleChange = (newTitle: string) => {
    setTitle(newTitle);
    setHasChanges(newTitle !== document?.title || content !== document?.content);
  };

  const handleSave = async () => {
    if (!hasChanges) return;

    try {
      setLoading(true);
      // Here you would typically save to your backend
      // For now, we'll just update the local state
      const updatedDocument = {
        ...document,
        title,
        content,
        format: 'markdown'
      } as Document;

      setDocument(updatedDocument);
      setHasChanges(false);

      // Show success message (you could use a snackbar here)
      console.log('Document saved successfully');
    } catch (error) {
      console.error('Error saving document:', error);
      setError('Failed to save document');
    } finally {
      setLoading(false);
    }
  };

  const handleExport = async () => {
    if (!content.trim()) {
      setError('Cannot export empty document');
      return;
    }

    try {
      setExporting(true);
      const response = await apiService.post('/api/user-documents/export', {
        content,
        format: exportFormat,
        title: title || 'document'
      }, {
        responseType: 'blob'
      });

      // Create download link
      const url = window.URL.createObjectURL(new Blob([response]));
      const link = document.createElement('a');
      link.href = url;

      const fileExtension = exportFormat;
      const fileName = `${title || 'document'}.${fileExtension}`;
      link.setAttribute('download', fileName);

      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);

      setExportDialogOpen(false);
    } catch (error) {
      console.error('Error exporting document:', error);
      setError('Failed to export document');
    } finally {
      setExporting(false);
    }
  };

  const handlePreview = async () => {
    try {
      const response = await apiService.post('/api/user-documents/preview', new URLSearchParams({
        content,
        format: 'html'
      }), {
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
      });

      if (response.success) {
        setPreviewContent(response.preview);
        setPreviewDialogOpen(true);
      } else {
        setError('Failed to generate preview');
      }
    } catch (error) {
      console.error('Error generating preview:', error);
      setError('Failed to generate preview');
    }
  };

  const getDocumentStats = () => {
    const words = content.trim().split(/\s+/).filter(word => word.length > 0).length;
    const characters = content.length;
    const lines = content.split('\n').length;

    return { words, characters, lines };
  };

  const stats = getDocumentStats();

  return (
    <Box sx={{ height: '100vh', display: 'flex', flexDirection: 'column' }}>
      {/* Header Toolbar */}
      <Paper elevation={1} sx={{ borderRadius: 0 }}>
        <Toolbar>
          <IconButton onClick={() => navigate(-1)} sx={{ mr: 2 }}>
            <BackIcon />
          </IconButton>

          <TextField
            value={title}
            onChange={(e) => handleTitleChange(e.target.value)}
            placeholder="Document Title"
            variant="standard"
            sx={{ flexGrow: 1, mr: 2 }}
            InputProps={{
              sx: { fontSize: '1.2rem', fontWeight: 500 }
            }}
          />

          {/* Document info chips */}
          <Box sx={{ display: 'flex', gap: 1, mr: 2 }}>
            {document?.template_used && (
              <Chip
                label={`Template: ${document.template_used}`}
                size="small"
                variant="outlined"
              />
            )}
            {location.state?.isImported && (
              <Chip
                label="Imported"
                size="small"
                color="info"
                variant="outlined"
              />
            )}
            {location.state?.isNew && (
              <Chip
                label="New"
                size="small"
                color="success"
                variant="outlined"
              />
            )}
          </Box>

          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSave}
            disabled={!hasChanges || loading}
            sx={{ mr: 1 }}
          >
            {loading ? <CircularProgress size={20} /> : 'Save'}
          </Button>

          <Button
            variant="outlined"
            startIcon={<PreviewIcon />}
            onClick={handlePreview}
            sx={{ mr: 1 }}
          >
            Preview
          </Button>

          <Button
            variant="outlined"
            startIcon={<ExportIcon />}
            onClick={() => setExportDialogOpen(true)}
            sx={{ mr: 1 }}
          >
            Export
          </Button>

          <IconButton onClick={(e) => setMenuAnchor(e.currentTarget)}>
            <MoreIcon />
          </IconButton>
        </Toolbar>
      </Paper>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" onClose={() => setError('')} sx={{ m: 2 }}>
          {error}
        </Alert>
      )}

      {/* Editor */}
      <Box sx={{ flexGrow: 1, display: 'flex' }}>
        <Box sx={{ flexGrow: 1 }}>
          <Editor
            height="100%"
            defaultLanguage="markdown"
            value={content}
            onChange={handleContentChange}
            theme="vs-light"
            options={{
              minimap: { enabled: false },
              wordWrap: 'on',
              fontSize: 14,
              lineHeight: 1.6,
              padding: { top: 16, bottom: 16 },
              scrollBeyondLastLine: false,
              automaticLayout: true
            }}
          />
        </Box>

        {/* Stats Sidebar */}
        <Paper
          elevation={1}
          sx={{
            width: 200,
            p: 2,
            borderRadius: 0,
            borderLeft: '1px solid',
            borderColor: 'divider'
          }}
        >
          <Typography variant="h6" gutterBottom>
            Document Stats
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Words
            </Typography>
            <Typography variant="h6">
              {stats.words.toLocaleString()}
            </Typography>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Characters
            </Typography>
            <Typography variant="h6">
              {stats.characters.toLocaleString()}
            </Typography>
          </Box>

          <Box sx={{ mb: 2 }}>
            <Typography variant="body2" color="text.secondary">
              Lines
            </Typography>
            <Typography variant="h6">
              {stats.lines.toLocaleString()}
            </Typography>
          </Box>

          {document?.created_at && (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Created
              </Typography>
              <Typography variant="caption">
                {new Date(document.created_at).toLocaleDateString()}
              </Typography>
            </Box>
          )}
        </Paper>
      </Box>

      {/* More Options Menu */}
      <Menu
        anchorEl={menuAnchor}
        open={Boolean(menuAnchor)}
        onClose={() => setMenuAnchor(null)}
      >
        <MenuItem onClick={() => {
          setMenuAnchor(null);
          setExportDialogOpen(true);
        }}>
          <ExportIcon sx={{ mr: 1 }} />
          Export Document
        </MenuItem>
        <MenuItem onClick={() => {
          setMenuAnchor(null);
          handlePreview();
        }}>
          <PreviewIcon sx={{ mr: 1 }} />
          Preview Document
        </MenuItem>
      </Menu>

      {/* Export Dialog */}
      <Dialog open={exportDialogOpen} onClose={() => setExportDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Export Document</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Export Format</InputLabel>
              <Select
                value={exportFormat}
                onChange={(e) => setExportFormat(e.target.value)}
                label="Export Format"
              >
                {exportFormats.map((format) => (
                  <MenuItem key={format.format} value={format.format}>
                    <Box>
                      <Typography variant="body1">{format.name}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {format.description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <Typography variant="body2" color="text.secondary">
              Document will be exported as: <strong>{title || 'document'}.{exportFormat}</strong>
            </Typography>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setExportDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleExport}
            disabled={exporting}
            startIcon={exporting ? <CircularProgress size={16} /> : <DownloadIcon />}
          >
            {exporting ? 'Exporting...' : 'Export'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Preview Dialog */}
      <Dialog
        open={previewDialogOpen}
        onClose={() => setPreviewDialogOpen(false)}
        maxWidth="md"
        fullWidth
      >
        <DialogTitle>Document Preview</DialogTitle>
        <DialogContent>
          <Box
            sx={{
              border: '1px solid',
              borderColor: 'divider',
              borderRadius: 1,
              p: 2,
              minHeight: 400,
              backgroundColor: 'background.paper'
            }}
            dangerouslySetInnerHTML={{ __html: previewContent }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPreviewDialogOpen(false)}>Close</Button>
          <Button
            variant="contained"
            onClick={() => {
              setPreviewDialogOpen(false);
              setExportDialogOpen(true);
            }}
          >
            Export Document
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default EditorView;