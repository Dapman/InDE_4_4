/**
 * ExportButton Component
 * Downloads a complete pursuit export as a ZIP file.
 *
 * v3.13: Innovator Experience Polish
 */

import { useState } from 'react';
import { Download, Loader2, CheckCircle, AlertCircle } from 'lucide-react';
import { Button } from '../ui/button';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '../ui/tooltip';
import { useAuthStore } from '../../stores/authStore';
import axios from 'axios';

export default function ExportButton({
  pursuitId,
  pursuitTitle = 'pursuit',
  variant = 'outline',
  size = 'sm',
  showLabel = true,
}) {
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');
  const token = useAuthStore((state) => state.token);

  const handleExport = async (e) => {
    // Prevent event propagation (important when wrapped in tooltip)
    e?.stopPropagation?.();
    e?.preventDefault?.();

    console.log('[ExportButton] Starting export for pursuit:', pursuitId);

    if (!pursuitId) {
      console.error('[ExportButton] No pursuit ID provided');
      setError('No pursuit selected');
      return;
    }

    if (!token) {
      console.error('[ExportButton] No auth token available');
      setError('Please log in again');
      return;
    }

    setLoading(true);
    setError('');
    setSuccess(false);

    try {
      console.log('[ExportButton] Fetching export via axios...');
      const response = await axios.get(`/api/pursuits/${pursuitId}/export`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
        responseType: 'blob',
      });

      console.log('[ExportButton] Response status:', response.status);

      // Get filename from header or generate one
      const contentDisposition = response.headers['content-disposition'];
      let filename = `inde_export_${pursuitTitle.replace(/[^a-z0-9]/gi, '_')}.zip`;

      if (contentDisposition) {
        const match = contentDisposition.match(/filename="(.+)"/);
        if (match) {
          filename = match[1];
        }
      }
      console.log('[ExportButton] Downloading as:', filename);

      // Get blob from axios response and ensure correct type
      const responseBlob = response.data;
      console.log('[ExportButton] Response blob size:', responseBlob.size, 'bytes');
      console.log('[ExportButton] Response blob type:', responseBlob.type);

      if (responseBlob.size === 0) {
        throw new Error('Export file is empty');
      }

      // Create blob and download
      const blob = new Blob([responseBlob], { type: 'application/zip' });
      console.log('[ExportButton] Final blob size:', blob.size, 'bytes');

      // Create blob URL
      const url = URL.createObjectURL(blob);

      // Open in new window - this bypasses some download restrictions
      const newWindow = window.open(url, '_blank');

      if (!newWindow) {
        // Popup blocked - fall back to link method
        console.log('[ExportButton] Popup blocked, using link method');
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        a.click();
      } else {
        console.log('[ExportButton] Opened in new window');
        // The new window will prompt to download or display the file
      }

      // Store reference to prevent GC
      window.__exportBlobUrl = url;

      console.log('[ExportButton] Download triggered successfully');
      setSuccess(true);
      setTimeout(() => setSuccess(false), 3000);
    } catch (err) {
      // Handle axios errors
      const errorMsg = err.response?.data?.detail || err.message || 'Export failed. Please try again.';
      setError(errorMsg);
      console.error('[ExportButton] Export failed:', err);
      setTimeout(() => setError(''), 5000);
    } finally {
      setLoading(false);
    }
  };

  const getButtonContent = () => {
    if (loading) {
      return (
        <>
          <Loader2 className="h-4 w-4 animate-spin" />
          {showLabel && <span>Generating...</span>}
        </>
      );
    }

    if (success) {
      return (
        <>
          <CheckCircle className="h-4 w-4 text-green-400" />
          {showLabel && <span>Downloaded!</span>}
        </>
      );
    }

    if (error) {
      return (
        <>
          <AlertCircle className="h-4 w-4 text-red-400" />
          {showLabel && <span>Failed</span>}
        </>
      );
    }

    return (
      <>
        <Download className="h-4 w-4" />
        {showLabel && <span>Export</span>}
      </>
    );
  };

  const button = (
    <Button
      variant={variant}
      size={size}
      onClick={handleExport}
      disabled={loading}
      className={
        success
          ? 'text-green-400 border-green-400/30'
          : error
          ? 'text-red-400 border-red-400/30'
          : 'text-zinc-400 hover:text-zinc-200'
      }
    >
      {getButtonContent()}
    </Button>
  );

  if (!showLabel) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>{button}</TooltipTrigger>
          <TooltipContent>
            <p>Export pursuit as ZIP</p>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return button;
}
