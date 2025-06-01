import React, { useState } from 'react';
import {
  Box,
  Container,
  Heading,
  Text,
  VStack,
  HStack,
  SimpleGrid,
  Flex,
  Switch,
  Icon,
  useColorModeValue,
  Spinner,
  Badge,
  useBreakpointValue
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';

// Анимация пульсации
const pulseAnimation = keyframes`
  0% { opacity: 0.6; transform: scale(0.98); }
  50% { opacity: 1; transform: scale(1); }
  100% { opacity: 0.6; transform: scale(0.98); }
`;

// Компонент функционального блока
interface FeatureBlockProps {
  icon: string;
  title: string;
  description: string;
}

const FeatureBlock: React.FC<FeatureBlockProps> = ({ icon, title, description }) => {
  const bgColor = useColorModeValue('white', 'gray.800');
  const borderColor = useColorModeValue('gray.100', 'gray.700');
  
  return (
    <Box
      p={5}
      bg={bgColor}
      borderRadius="lg"
      boxShadow="md"
      border="1px solid"
      borderColor={borderColor}
      transition="all 0.3s ease"
      _hover={{ transform: 'translateY(-5px)', boxShadow: 'lg' }}
    >
      <Flex direction="column" align="flex-start">
        <Box fontSize="2xl" mb={3}>{icon}</Box>
        <Heading as="h3" size="md" mb={2}>{title}</Heading>
        <Text fontSize="sm">{description}</Text>
      </Flex>
    </Box>
  );
};

// Компонент версии приложения (веб/мобильная)
interface VersionComparisonProps {
  title: string;
  icon: string;
  benefits: string[];
}

const VersionComparison: React.FC<VersionComparisonProps> = ({ title, icon, benefits }) => {
  const bgColor = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  
  return (
    <Box
      p={5}
      bg={bgColor}
      borderRadius="lg"
      boxShadow="sm"
      border="1px solid"
      borderColor={borderColor}
    >
      <Flex align="center" mb={3}>
        <Box fontSize="2xl" mr={2}>{icon}</Box>
        <Heading as="h3" size="md">{title}</Heading>
      </Flex>
      
      <VStack align="start" spacing={2}>
        {benefits.map((benefit, index) => (
          <Flex key={index} align="center">
            <Box as="span" mr={2} color="green.500">✓</Box>
            <Text fontSize="sm">{benefit}</Text>
          </Flex>
        ))}
      </VStack>
    </Box>
  );
};

// Основной компонент превью приложения
const AppPreview: React.FC = () => {
  const [isMobile, setIsMobile] = useState(false);
  const headingSize = useBreakpointValue({ base: "xl", md: "2xl" });
  const containerWidth = useBreakpointValue({ base: "100%", md: "90%", lg: "80%" });
  
  // Цвета для стилизации
  const glassBg = useColorModeValue('rgba(255, 255, 255, 0.8)', 'rgba(26, 32, 44, 0.8)');
  const borderColor = useColorModeValue('gray.200', 'gray.700');
  const gradientStart = useColorModeValue('blue.50', 'blue.900');
  const gradientEnd = useColorModeValue('purple.50', 'purple.900');
  
  // Размеры для контейнера превью
  const previewWidth = isMobile ? { base: "280px", md: "320px" } : { base: "100%", md: "800px" };
  const previewHeight = isMobile ? { base: "500px", md: "600px" } : { base: "400px", md: "600px" };
  
  // Данные о функциях
  const features = [
    {
      icon: "📊",
      title: "Аналитика потребностей",
      description: "Отслеживайте и анализируйте свои психологические потребности в динамике для лучшего понимания себя."
    },
    {
      icon: "📝",
      title: "Умные дневники",
      description: "Структурированные дневники настроения и мыслей с автоматическим анализом паттернов и триггеров."
    },
    {
      icon: "🎯",
      title: "Персональные рекомендации",
      description: "Получайте рекомендации по активностям, адаптированные под ваши уникальные потребности и предпочтения."
    },
    {
      icon: "🧠",
      title: "Упражнения осознанности",
      description: "Библиотека упражнений для развития внимательности, эмоциональной регуляции и психологической гибкости."
    }
  ];
  
  // Данные о преимуществах версий
  const webBenefits = [
    "Расширенная аналитика и графики",
    "Удобный большой экран для дневниковых записей",
    "Расширенные возможности планирования",
    "Интеграция с календарем и заметками",
    "Полная клавиатура для быстрого ввода"
  ];
  
  const mobileBenefits = [
    "Доступ в любом месте и в любое время",
    "Мгновенные уведомления и напоминания",
    "Упрощенный интерфейс для быстрого использования",
    "Возможность делать фото и аудиозаписи",
    "Отслеживание активности и местоположения"
  ];
  
  const handleToggleChange = () => {
    setIsMobile(!isMobile);
  };
  
  return (
    <Box py={16} position="relative" overflow="hidden">
      {/* Декоративные элементы фона */}
      <Box
        position="absolute"
        top="-20%"
        right="-10%"
        width="500px"
        height="500px"
        bg={gradientStart}
        borderRadius="full"
        opacity="0.4"
        zIndex={-1}
      />
      <Box
        position="absolute"
        bottom="-30%"
        left="-15%"
        width="600px"
        height="600px"
        bg={gradientEnd}
        borderRadius="full"
        opacity="0.3"
        zIndex={-1}
      />
      
      <Container maxW="1200px">
        <VStack spacing={12} align="stretch">
          {/* Заголовок секции */}
          <Box textAlign="center" maxW="800px" mx="auto">
            <Heading as="h2" size={headingSize} mb={4}>
              Посмотрите, как выглядит ваш персональный психолог
            </Heading>
            <Text fontSize="lg" color="gray.600">
              Интуитивно понятный интерфейс и продуманный опыт использования — 
              мы сделали всё, чтобы забота о психическом здоровье была простой и приятной
            </Text>
          </Box>
          
          {/* Переключатель веб/мобильной версии */}
          <Flex justify="center" mb={6}>
            <HStack spacing={4}>
              <Text 
                fontWeight={!isMobile ? "bold" : "normal"}
                color={!isMobile ? "blue.500" : "gray.500"}
              >
                Веб-версия
              </Text>
              <Switch 
                colorScheme="blue" 
                size="lg" 
                isChecked={isMobile} 
                onChange={handleToggleChange}
              />
              <Text 
                fontWeight={isMobile ? "bold" : "normal"}
                color={isMobile ? "blue.500" : "gray.500"}
              >
                Мобильная версия
              </Text>
            </HStack>
          </Flex>
          
          {/* Контейнер для демо-интерфейса */}
          <Flex justify="center" mb={8}>
            <Box
              width={previewWidth}
              height={previewHeight}
              bg={glassBg}
              backdropFilter="blur(10px)"
              borderRadius={isMobile ? "24px" : "lg"}
              boxShadow="xl"
              border="1px solid"
              borderColor={borderColor}
              position="relative"
              overflow="hidden"
              transition="all 0.5s ease"
            >
              {/* Фоновый градиент */}
              <Box
                position="absolute"
                top={0}
                left={0}
                right={0}
                bottom={0}
                bgGradient={`linear(to-br, ${gradientStart}, ${gradientEnd})`}
                opacity={0.15}
                zIndex={0}
              />
              
              {/* Плашка "В разработке" */}
              <VStack
                position="absolute"
                top="50%"
                left="50%"
                transform="translate(-50%, -50%)"
                spacing={4}
                textAlign="center"
                zIndex={1}
                animation={`${pulseAnimation} 3s infinite ease-in-out`}
              >
                <Text fontSize="6xl">🚧</Text>
                <Heading size="lg">В разработке</Heading>
                <Text>Интерактивный дашборд скоро будет доступен</Text>
                <Spinner size="xl" color="blue.500" thickness="4px" speed="0.8s" mt={4} />
                <Badge colorScheme="blue" fontSize="md" mt={2}>
                  {isMobile ? "Мобильная версия" : "Веб-версия"}
                </Badge>
              </VStack>
              
              {/* Визуальная рамка мобильного устройства */}
              {isMobile && (
                <>
                  <Box 
                    position="absolute" 
                    top="12px" 
                    left="50%" 
                    transform="translateX(-50%)" 
                    width="40%" 
                    height="20px" 
                    bg="black" 
                    borderRadius="full"
                    zIndex={2}
                  />
                  <Box 
                    position="absolute"
                    bottom="20px"
                    left="50%"
                    transform="translateX(-50%)"
                    width="30%"
                    height="4px"
                    bg="black"
                    borderRadius="full"
                    zIndex={2}
                  />
                </>
              )}
              
              {/* Хедер в веб-версии */}
              {!isMobile && (
                <Box 
                  position="absolute" 
                  top={0} 
                  left={0} 
                  right={0} 
                  height="60px" 
                  bg="white" 
                  borderBottom="1px solid" 
                  borderColor="gray.200"
                  display="flex"
                  alignItems="center"
                  px={4}
                  zIndex={2}
                >
                  <Text fontWeight="bold" fontSize="lg">PsyBalans</Text>
                  <Box flex="1" />
                  <HStack spacing={4}>
                    <Box w="40px" h="10px" bg="gray.200" borderRadius="full" />
                    <Box w="40px" h="10px" bg="gray.200" borderRadius="full" />
                    <Box w="40px" h="10px" bg="gray.200" borderRadius="full" />
                  </HStack>
                </Box>
              )}
            </Box>
          </Flex>
          
          {/* Описание функций */}
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8}>
            {features.map((feature, index) => (
              <FeatureBlock
                key={index}
                icon={feature.icon}
                title={feature.title}
                description={feature.description}
              />
            ))}
          </SimpleGrid>
          
          {/* Сравнение веб и мобильной версий */}
          <Heading as="h3" size="lg" textAlign="center" mt={8} mb={6}>
            Выберите удобный формат
          </Heading>
          
          <SimpleGrid columns={{ base: 1, md: 2 }} spacing={8}>
            <VersionComparison
              title="ВЕБ-ВЕРСИЯ"
              icon="💻"
              benefits={webBenefits}
            />
            <VersionComparison
              title="МОБИЛЬНАЯ ВЕРСИЯ"
              icon="📱"
              benefits={mobileBenefits}
            />
          </SimpleGrid>
          
          {/* Информация о бета-тестировании */}
          <Box
            mt={10}
            p={6}
            bg={glassBg}
            backdropFilter="blur(10px)"
            borderRadius="lg"
            boxShadow="md"
            border="1px solid"
            borderColor={borderColor}
            textAlign="center"
          >
            <Badge colorScheme="purple" fontSize="md" mb={3}>
              Скоро запуск
            </Badge>
            <Heading as="h3" size="md" mb={3}>
              Хотите протестировать приложение первыми?
            </Heading>
            <Text>
              Запишитесь в список ожидания, чтобы получить ранний доступ к бета-версии 
              приложения PsyBalans и возможность влиять на его развитие.
            </Text>
          </Box>
        </VStack>
      </Container>
    </Box>
  );
};

export default AppPreview;