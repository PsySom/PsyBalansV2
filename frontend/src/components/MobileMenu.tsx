import React, { useEffect, useRef } from 'react';
import {
  Box,
  Flex,
  VStack,
  Button,
  Divider,
  CloseButton,
  Portal,
  Slide
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';
import { Link as RouterLink } from 'react-router-dom';

interface MobileMenuProps {
  isOpen: boolean;
  onClose: () => void;
  navItems: Array<{ to: string; label: string }>;
  isAuthenticated: boolean;
  onLoginClick: () => void;
  onRegisterClick: () => void;
}

// Keyframes для staggered анимации
const fadeInUp = keyframes`
  0% { opacity: 0; transform: translateY(20px); }
  100% { opacity: 1; transform: translateY(0); }
`;

// Компонент отдельного пункта меню с анимацией
const MobileMenuItem = ({ 
  to, 
  label, 
  onClick, 
  delay 
}: { 
  to: string; 
  label: string; 
  onClick: () => void; 
  delay: number;
}) => {
  const animation = `${fadeInUp} 0.4s ease forwards ${delay}s`;

  return (
    <Box 
      as={RouterLink}
      to={to}
      py={4}
      px={6}
      width="100%"
      fontWeight="500"
      fontSize="lg"
      color="text-primary"
      transition="all 0.3s ease"
      _hover={{ 
        color: "primary-action", 
        bg: "rgba(72, 187, 120, 0.05)"
      }}
      onClick={onClick}
      className="mobile-nav-link"
      opacity="0"
      sx={{ animation }}
      tabIndex={0}
      role="menuitem"
    >
      {label}
    </Box>
  );
};

// Основной компонент мобильного меню
const MobileMenu: React.FC<MobileMenuProps> = ({ 
  isOpen, 
  onClose, 
  navItems, 
  isAuthenticated,
  onLoginClick,
  onRegisterClick
}) => {
  // Фоновый цвет меню с glassmorphism эффектом
  const bgColor = "rgba(255, 255, 255, 0.85)";
  const menuRef = useRef<HTMLDivElement>(null);
  
  // Обработчик клика вне меню
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        onClose();
      }
    };
    
    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
      // Предотвращаем скролл страницы при открытом меню
      document.body.style.overflow = 'hidden';
    } else {
      // Восстанавливаем скролл страницы при закрытом меню
      document.body.style.overflow = '';
    }
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
      document.body.style.overflow = '';
    };
  }, [isOpen, onClose]);
  
  // Обработчик клавиши Escape
  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    };
    
    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
    }
    
    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [isOpen, onClose]);

  return (
    <Portal>
      {/* Затемняющий фон с анимацией */}
      <Box
        position="fixed"
        top="0"
        left="0"
        right="0"
        bottom="0"
        bg="rgba(0, 0, 0, 0.5)"
        zIndex="var(--z-index-modal-backdrop)"
        opacity={isOpen ? 1 : 0}
        pointerEvents={isOpen ? "auto" : "none"}
        transition="opacity 0.3s ease"
        className="mobile-menu-backdrop"
        aria-hidden="true"
        onClick={onClose}
      />
      
      {/* Выдвижное меню сверху */}
      <Slide 
        in={isOpen} 
        direction="top" 
        style={{ 
          zIndex: 'var(--z-index-modal)',
          width: '100%',
          height: '100vh',
          position: 'fixed',
          top: 0,
          left: 0
        }}
      >
        <Box
          ref={menuRef}
          bg={bgColor}
          backdropFilter="blur(20px)"
          boxShadow="var(--shadow-medium)"
          borderBottomLeftRadius="var(--border-radius-large)"
          borderBottomRightRadius="var(--border-radius-large)"
          maxHeight="85vh"
          height="auto"
          overflowY="auto"
          className="mobile-menu"
          role="menu"
          aria-label="Мобильное меню навигации"
        >
          {/* Шапка мобильного меню */}
          <Flex 
            justify="space-between" 
            align="center" 
            p={6} 
            borderBottom="1px solid" 
            borderColor="rgba(255, 255, 255, 0.2)"
          >
            <Box 
              fontSize="xl" 
              fontWeight="bold" 
              color="primary-action"
              opacity="0"
              sx={{ animation: `${fadeInUp} 0.4s ease forwards 0.1s` }}
            >
              Меню
            </Box>
            <CloseButton 
              onClick={onClose} 
              size="lg" 
              color="text-primary"
              aria-label="Закрыть меню"
              opacity="0"
              sx={{ animation: `${fadeInUp} 0.4s ease forwards 0.1s` }}
            />
          </Flex>
          
          {/* Пункты меню с анимацией */}
          <VStack 
            spacing={0} 
            align="stretch" 
            py={4} 
            divider={<Divider borderColor="rgba(0, 0, 0, 0.05)" />}
          >
            {navItems.map((item, index) => (
              <MobileMenuItem 
                key={item.to} 
                to={item.to} 
                label={item.label} 
                onClick={onClose}
                delay={0.15 + index * 0.05} // Staggered эффект
              />
            ))}
          </VStack>
          
          {/* Кнопки авторизации для неавторизованных пользователей */}
          {!isAuthenticated && (
            <Flex 
              direction="column" 
              p={6} 
              gap={3} 
              mt={2}
              borderTop="1px solid" 
              borderColor="rgba(0, 0, 0, 0.05)"
            >
              <Button 
                className="btn btn-primary"
                onClick={() => {
                  onLoginClick();
                  onClose();
                }}
                opacity="0"
                sx={{ animation: `${fadeInUp} 0.4s ease forwards ${0.2 + navItems.length * 0.05}s` }}
                aria-label="Войти в аккаунт"
              >
                Войти
              </Button>
              <Button 
                variant="outline"
                className="btn btn-secondary"
                onClick={() => {
                  onRegisterClick();
                  onClose();
                }}
                opacity="0"
                sx={{ animation: `${fadeInUp} 0.4s ease forwards ${0.25 + navItems.length * 0.05}s` }}
                aria-label="Зарегистрироваться"
              >
                Регистрация
              </Button>
            </Flex>
          )}
        </Box>
      </Slide>
    </Portal>
  );
};

export default MobileMenu;