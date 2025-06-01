import React from 'react';
import { Box, useColorModeValue } from '@chakra-ui/react';

interface GlassBoxProps extends React.ComponentProps<typeof Box> {
  blurStrength?: number;
  opacity?: number;
  borderOpacity?: number;
  children: React.ReactNode;
}

/**
 * Компонент с эффектом матового стекла (glass morphism)
 */
const GlassBox: React.FC<GlassBoxProps> = ({
  blurStrength = 20,
  opacity = 0.85,
  borderOpacity = 0.2,
  children,
  ...props
}) => {
  const bgColor = useColorModeValue(
    `rgba(255, 255, 255, ${opacity})`,
    `rgba(26, 32, 44, ${opacity})`
  );
  
  const borderColor = useColorModeValue(
    `rgba(255, 255, 255, ${borderOpacity + 0.3})`,
    `rgba(255, 255, 255, ${borderOpacity})`
  );

  return (
    <Box
      bg={bgColor}
      backdropFilter={`blur(${blurStrength}px)`}
      borderWidth="1px"
      borderColor={borderColor}
      borderRadius="md"
      className="glass-effect"
      {...props}
      sx={{
        // Для Firefox, который не поддерживает backdrop-filter
        '@supports not (backdrop-filter: blur(1px))': {
          bg: useColorModeValue(
            `rgba(255, 255, 255, ${opacity + 0.1})`,
            `rgba(26, 32, 44, ${opacity + 0.1})`
          ),
        },
        // Для Safari и других WebKit браузеров
        WebkitBackdropFilter: `blur(${blurStrength}px)`,
        ...props.sx
      }}
    >
      {children}
    </Box>
  );
};

export default GlassBox;