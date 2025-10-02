import {
    Add as AddIcon,
    Upload as UploadIcon
} from '@mui/icons-material';
import {
    Alert,
    Box,
    Button,
    Card,
    CardContent,
    Chip,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    Fab,
    FormControl,
    Grid,
    InputLabel,
    MenuItem,
    Select,
    TextField,
    Tooltip,
    Typography
} from '@mui/material';
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';

interface Template {
  id: string;
  name: string;
  description: string;
  format: string;
  preview: string;
}

interface ExportFormat {
  format: string;
  name: string;
  description: string;
}

const DocumentCreator: React.FC = () => {
  const navigate = useNavigate();
  const [templates, setTemplates] = useState<Template[]>([]);
  const [exportFormats, setExportFormats] = useState<ExportFormat[]>([]);
  const [loading, setLoading] = useState(true);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [selectedTemplate, setSelectedTemplate] = useState<string>('');
  const [documentTitle, setDocumentTitle] = useState('');
  const [importDialogOpen, setImportDialogOpen] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string>('');

  useEffect(() => {
    loadTemplatesAndFormats();
  }, []);

  const loadTemplatesAndFormats = async () => {
    try {
      setLoading(true);
      const [templatesResponse, formatsResponse] = await Promise.all([
        apiService.get('/api/user-documents/templates'),
        apiService.get('/api/user-documents/supported-formats')
      ]);

      if (templatesResponse.success) {
        setTemplates(templatesResponse.templates);
      }

      setExportFormats(formatsResponse.export_formats || []);
    } catch (error) {
      console.error('Error loading templates and formats:', error);
      setError('Failed to load document templates');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateDocument = async () => {
    if (!selectedTemplate) {
      setError('Please select a template');
      return;
    }

    try {
      setLoading(true);
      const response = await apiService.post('/api/user-documents/create', {
        template_id: selectedTemplate,
        title: documentTitle || undefined
      });

      if (response.success) {
        // Navigate to editor with the new document
        navigate('/editor', {
          state: {
            document: response.document,
            isNew: true
          }
        });
      } else {
        setError(response.error || 'Failed to create document');
      }
    } catch (error) {
      console.error('Error creating document:', error);
      setError('Failed to create document');
    } finally {
      setLoading(false);
      setCreateDialogOpen(false);
      setSelectedTemplate('');
      setDocumentTitle('');
    }
  };

  const handleImportDocument = async () => {
    if (!selectedFile) {
      setError('Please select a file to import');
      return;
    }

    try {
      setLoading(true);
      const formData = new FormData();
      formData.append('file', selectedFile);

      const response = await apiService.post('/api/user-documents/import', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      if (response.success) {
        // Navigate to editor with the imported document
        navigate('/editor', {
          state: {
            document: response.document,
            isImported: true
          }
        });
      } else {
        setError(response.error || 'Failed to import document');
      }
    } catch (error) {
      console.error('Error importing document:', error);
      setError('Failed to import document');
    } finally {
      setLoading(false);
      setImportDialogOpen(false);
      setSelectedFile(null);
    }
  };

  const getTemplateIcon = (templateId: string) => {
    const iconMap: { [key: string]: string } = {
      'blank_document': '📄',
      'letter': '✉️',
      'resume': '👔',
      'report': '📊',
      'meeting_notes': '📝',
      'project_plan': '📋'
    };
    return iconMap[templateId] || '📄';
  };

  if (loading && templates.length === 0) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box sx={{ p: 3 }}>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Create New Document
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Choose a template to get started or import an existing document
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError('')}>
          {error}
        </Alert>
      )}

      {/* Quick Actions */}
      <Box sx={{ mb: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => setCreateDialogOpen(true)}
          size="large"
        >
          Create from Template
        </Button>
        <Button
          variant="outlined"
          startIcon={<UploadIcon />}
          onClick={() => setImportDialogOpen(true)}
          size="large"
        >
          Import Document
        </Button>
      </Box>

      {/* Template Grid */}
      <Typography variant="h5" component="h2" gutterBottom>
        Document Templates
      </Typography>
      <Grid container spacing={3}>
        {templates.map((template) => (
          <Grid item xs={12} sm={6} md={4} key={template.id}>
            <Card
              sx={{
                height: '100%',
                cursor: 'pointer',
                transition: 'transform 0.2s, box-shadow 0.2s',
                '&:hover': {
                  transform: 'translateY(-4px)',
                  boxShadow: 4
                }
              }}
              onClick={() => {
                setSelectedTemplate(template.id);
                setCreateDialogOpen(true);
              }}
            >
              <CardContent>
                <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
                  <Typography variant="h2" sx={{ mr: 2 }}>
                    {getTemplateIcon(template.id)}
                  </Typography>
                  <Typography variant="h6" component="h3">
                    {template.name}
                  </Typography>
                </Box>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                  {template.description}
                </Typography>
                <Chip
                  label={template.format.toUpperCase()}
                  size="small"
                  color="primary"
                  variant="outlined"
                />
                <Typography
                  variant="caption"
                  sx={{
                    display: 'block',
                    mt: 2,
                    fontFamily: 'monospace',
                    backgroundColor: 'grey.100',
                    p: 1,
                    borderRadius: 1,
                    maxHeight: '60px',
                    overflow: 'hidden'
                  }}
                >
                  {template.preview}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Create Document Dialog */}
      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create New Document</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <FormControl fullWidth sx={{ mb: 3 }}>
              <InputLabel>Template</InputLabel>
              <Select
                value={selectedTemplate}
                onChange={(e) => setSelectedTemplate(e.target.value)}
                label="Template"
              >
                {templates.map((template) => (
                  <MenuItem key={template.id} value={template.id}>
                    <Box sx={{ display: 'flex', alignItems: 'center' }}>
                      <Typography sx={{ mr: 1 }}>{getTemplateIcon(template.id)}</Typography>
                      {template.name}
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
              label="Document Title (Optional)"
              value={documentTitle}
              onChange={(e) => setDocumentTitle(e.target.value)}
              placeholder="Enter a title for your document"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleCreateDocument}
            disabled={!selectedTemplate || loading}
          >
            {loading ? <CircularProgress size={20} /> : 'Create Document'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Import Document Dialog */}
      <Dialog open={importDialogOpen} onClose={() => setImportDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Import Document</DialogTitle>
        <DialogContent>
          <Box sx={{ pt: 1 }}>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Upload a document file to convert it to an editable format
            </Typography>

            <Box
              sx={{
                border: '2px dashed',
                borderColor: selectedFile ? 'primary.main' : 'grey.300',
                borderRadius: 1,
                p: 3,
                textAlign: 'center',
                cursor: 'pointer',
                '&:hover': {
                  borderColor: 'primary.main',
                  backgroundColor: 'action.hover'
                }
              }}
              component="label"
            >
              <input
                type="file"
                hidden
                accept=".txt,.md,.docx,.pdf,.html,.rtf"
                onChange={(e) => setSelectedFile(e.target.files?.[0] || null)}
              />
              <UploadIcon sx={{ fontSize: 48, color: 'grey.400', mb: 1 }} />
              <Typography variant="body1">
                {selectedFile ? selectedFile.name : 'Click to select a file'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Supported: TXT, MD, DOCX, PDF, HTML, RTF
              </Typography>
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setImportDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleImportDocument}
            disabled={!selectedFile || loading}
          >
            {loading ? <CircularProgress size={20} /> : 'Import Document'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Floating Action Button for Quick Create */}
      <Tooltip title="Quick Create Blank Document">
        <Fab
          color="primary"
          sx={{ position: 'fixed', bottom: 16, right: 16 }}
          onClick={() => {
            setSelectedTemplate('blank_document');
            setCreateDialogOpen(true);
          }}
        >
          <AddIcon />
        </Fab>
      </Tooltip>
    </Box>
  );
};

export default DocumentCreator;