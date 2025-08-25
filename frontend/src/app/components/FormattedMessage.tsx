import React from 'react';

interface FormattedMessageProps {
  text: string;
  className?: string;
}

const FormattedMessage: React.FC<FormattedMessageProps> = ({ text, className = '' }) => {
  // Function to safely escape HTML and format the text
  const formatText = (text: string): string => {
    // First, escape any HTML to prevent XSS
    const escapedText = text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#x27;');

    // Convert line breaks to <br> tags
    const withLineBreaks = escapedText.replace(/\n/g, '<br />');
    
    return withLineBreaks;
  };

  return (
    <div 
      className={className}
      style={{ 
        whiteSpace: 'pre-line',
        wordWrap: 'break-word',
        lineHeight: '1.5'
      }}
      dangerouslySetInnerHTML={{ __html: formatText(text) }}
    />
  );
};

export default FormattedMessage;
