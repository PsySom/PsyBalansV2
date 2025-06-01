import React from 'react';
import { Text, TextProps } from '@chakra-ui/react';

interface GradientTextProps extends TextProps {
  gradient?: string;
  children: React.ReactNode;
}

/**
 * Компонент для отображения текста с градиентной заливкой
 */
const GradientText: React.FC<GradientTextProps> = ({
  gradient = 'linear-gradient(135deg, var(--primary-action), var(--primary-action-dark))',
  children,
  ...props
}) => {
  return (
    <Text
      as="span"
      sx={{
        background: gradient,
        WebkitBackgroundClip: 'text',
        WebkitTextFillColor: 'transparent',
        backgroundClip: 'text',
        textFillColor: 'transparent',
        display: 'inline-block',
      }}
      {...props}
    >
      {children}
    </Text>
  );
};

export default GradientText;