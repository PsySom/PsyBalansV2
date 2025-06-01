import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Heading,
  Text,
  Table,
  Thead,
  Tbody,
  Tr,
  Th,
  Td,
  Badge,
  HStack,
  VStack,
  useColorModeValue,
  useBreakpointValue,
  SimpleGrid,
  Flex,
  Tooltip
} from '@chakra-ui/react';
import { keyframes } from '@emotion/react';

interface ComparisonItem {
  parameter: string;
  description: string;
  psybalans: {
    value: string;
    rating: 'excellent' | 'good' | 'average' | 'poor';
    details: string;
  };
  traditional: {
    value: string;
    rating: 'excellent' | 'good' | 'average' | 'poor';
    details: string;
  };
}

// Анимация появления строк
const fadeInUp = keyframes`
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
`;

// Компонент мобильной карточки
interface MobileCardProps {
  item: ComparisonItem;
  index: number;
}

const MobileCard: React.FC<MobileCardProps> = ({ item, index }) => {
  const [isHovered, setIsHovered] = useState(false);
  const bgColor = useColorModeValue('white', 'gray.700');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const animation = `${fadeInUp} 0.5s ease forwards ${index * 0.1 + 0.2}s`;
  
  // Цвета для рейтингов
  const ratingColors = {
    excellent: 'green',
    good: 'teal',
    average: 'blue',
    poor: 'gray'
  };
  
  return (
    <Box
      p={4}
      borderRadius="lg"
      boxShadow="md"
      bg={bgColor}
      borderWidth="1px"
      borderColor={borderColor}
      transition="all 0.3s ease"
      _hover={{ transform: 'translateY(-5px)', boxShadow: 'lg' }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      opacity="0"
      sx={{ animation }}
      position="relative"
      overflow="hidden"
    >
      {/* Параметр сравнения */}
      <Heading as="h3" size="sm" mb={2}>
        {item.parameter}
      </Heading>
      <Text fontSize="sm" mb={4} noOfLines={isHovered ? undefined : 2}>
        {item.description}
      </Text>
      
      {/* Сравнение */}
      <SimpleGrid columns={2} spacing={3} mt={3}>
        <VStack align="start" spacing={1}>
          <Text fontWeight="bold" fontSize="sm">PsyBalans</Text>
          <Badge colorScheme={ratingColors[item.psybalans.rating]}>
            {item.psybalans.value}
          </Badge>
          <Text fontSize="xs" color="gray.500" noOfLines={isHovered ? undefined : 1}>
            {item.psybalans.details}
          </Text>
        </VStack>
        
        <VStack align="start" spacing={1}>
          <Text fontWeight="bold" fontSize="sm">Традиционный подход</Text>
          <Badge colorScheme={ratingColors[item.traditional.rating]}>
            {item.traditional.value}
          </Badge>
          <Text fontSize="xs" color="gray.500" noOfLines={isHovered ? undefined : 1}>
            {item.traditional.details}
          </Text>
        </VStack>
      </SimpleGrid>
      
      {/* Индикатор "нажмите для подробностей" */}
      {!isHovered && (
        <Text 
          fontSize="xs" 
          color="blue.500" 
          position="absolute" 
          bottom="2" 
          right="2"
        >
          Нажмите для подробностей
        </Text>
      )}
    </Box>
  );
};

const ComparisonTable: React.FC = () => {
  const isMobile = useBreakpointValue({ base: true, md: false });
  const [hoveredRow, setHoveredRow] = useState<number | null>(null);
  const tableRef = useRef<HTMLTableElement>(null);
  const [isTableVisible, setIsTableVisible] = useState(false);
  
  // Фон и стили для таблицы
  const headerBg = useColorModeValue('gray.50', 'gray.800');
  const borderColor = useColorModeValue('gray.200', 'gray.600');
  const psybalansBg = useColorModeValue('blue.50', 'blue.900');
  const traditionalBg = useColorModeValue('gray.50', 'gray.700');
  const hoverBg = useColorModeValue('gray.50', 'gray.700');
  
  // Наблюдатель пересечения для анимации таблицы
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          setIsTableVisible(true);
          observer.disconnect();
        }
      },
      { threshold: 0.1 }
    );
    
    if (tableRef.current) {
      observer.observe(tableRef.current);
    }
    
    return () => observer.disconnect();
  }, []);
  
  // Данные для сравнительной таблицы
  const comparisonData: ComparisonItem[] = [
    {
      parameter: "Доступность",
      description: "Возможность получить поддержку в любое время и в любом месте",
      psybalans: {
        value: "24/7",
        rating: "excellent",
        details: "Доступно в любое время суток, без ограничений по расписанию"
      },
      traditional: {
        value: "По записи",
        rating: "average",
        details: "Ограничено рабочим временем специалиста и его загруженностью"
      }
    },
    {
      parameter: "Стоимость",
      description: "Финансовые затраты на получение психологической поддержки",
      psybalans: {
        value: "Доступно",
        rating: "excellent",
        details: "Значительно ниже стоимость по сравнению с традиционными подходами"
      },
      traditional: {
        value: "Высокая",
        rating: "poor",
        details: "Регулярные сессии требуют существенных финансовых вложений"
      }
    },
    {
      parameter: "Конфиденциальность",
      description: "Уровень приватности и анонимности при работе с психологическими проблемами",
      psybalans: {
        value: "Полная",
        rating: "excellent",
        details: "Возможность полностью анонимного использования из комфортной среды"
      },
      traditional: {
        value: "Высокая",
        rating: "good",
        details: "Несмотря на профессиональную этику, требуется личное присутствие"
      }
    },
    {
      parameter: "Персонализация",
      description: "Адаптация подхода под индивидуальные особенности и потребности",
      psybalans: {
        value: "Алгоритмическая",
        rating: "good",
        details: "Интеллектуальные алгоритмы адаптируют рекомендации к потребностям"
      },
      traditional: {
        value: "Индивидуальная",
        rating: "excellent",
        details: "Полностью индивидуальный подход с учетом специфики личности"
      }
    },
    {
      parameter: "Системность",
      description: "Регулярность и последовательность психологической работы",
      psybalans: {
        value: "Высокая",
        rating: "excellent",
        details: "Ежедневное взаимодействие и отслеживание изменений"
      },
      traditional: {
        value: "Средняя",
        rating: "average",
        details: "Обычно одна сессия в неделю или реже"
      }
    },
    {
      parameter: "Формат работы",
      description: "Способ взаимодействия и методы психологической работы",
      psybalans: {
        value: "Интерактивный",
        rating: "good",
        details: "Разнообразные форматы: трекеры, дневники, рекомендации и упражнения"
      },
      traditional: {
        value: "Диалоговый",
        rating: "good",
        details: "Преимущественно разговорный формат с упражнениями на дом"
      }
    },
    {
      parameter: "Экстренная поддержка",
      description: "Возможность получить помощь в кризисной ситуации",
      psybalans: {
        value: "Базовая",
        rating: "average",
        details: "Алгоритмы антикризисной поддержки и ресурсы самопомощи"
      },
      traditional: {
        value: "Ограниченная",
        rating: "average",
        details: "Зависит от доступности специалиста в момент кризиса"
      }
    }
  ];
  
  // Функция для рендеринга значка рейтинга
  const renderRatingBadge = (rating: 'excellent' | 'good' | 'average' | 'poor') => {
    const colors = {
      excellent: 'green',
      good: 'teal',
      average: 'blue',
      poor: 'gray'
    };
    
    const labels = {
      excellent: 'Отлично',
      good: 'Хорошо',
      average: 'Средне',
      poor: 'Слабо'
    };
    
    return (
      <Badge colorScheme={colors[rating]} fontSize="xs">
        {labels[rating]}
      </Badge>
    );
  };
  
  return (
    <Box>
      <Heading as="h2" size="lg" mb={6} textAlign="center">
        PsyBalans vs Традиционные подходы
      </Heading>
      
      {isMobile ? (
        // Мобильный вид в виде карточек
        <SimpleGrid columns={1} spacing={4}>
          {comparisonData.map((item, index) => (
            <MobileCard key={index} item={item} index={index} />
          ))}
        </SimpleGrid>
      ) : (
        // Десктопный вид в виде таблицы с glassmorphism эффектом
        <Box
          ref={tableRef}
          position="relative"
          borderRadius="xl"
          overflow="hidden"
          boxShadow="xl"
          bg={useColorModeValue('rgba(255, 255, 255, 0.8)', 'rgba(26, 32, 44, 0.8)')}
          backdropFilter="blur(10px)"
          borderWidth="1px"
          borderColor={borderColor}
          sx={{
            // Кастомный скроллбар
            '&::-webkit-scrollbar': {
              width: '10px',
              height: '10px',
            },
            '&::-webkit-scrollbar-track': {
              bg: 'rgba(0, 0, 0, 0.05)',
            },
            '&::-webkit-scrollbar-thumb': {
              bg: 'rgba(0, 0, 0, 0.2)',
              borderRadius: '20px',
            },
            '&::-webkit-scrollbar-thumb:hover': {
              bg: 'rgba(0, 0, 0, 0.3)',
            },
            // Плавный скролл
            scrollBehavior: 'smooth',
          }}
        >
          <Table variant="simple">
            <Thead 
              position="sticky" 
              top={0} 
              zIndex={1}
              bg={headerBg}
              boxShadow="sm"
            >
              <Tr>
                <Th width="15%" borderColor={borderColor}>Параметр</Th>
                <Th width="25%" borderColor={borderColor}>Описание</Th>
                <Th width="30%" bg={psybalansBg} borderColor={borderColor}>
                  <HStack spacing={2}>
                    <Text>PsyBalans</Text>
                    <Badge colorScheme="blue" fontSize="xs">Digital</Badge>
                  </HStack>
                </Th>
                <Th width="30%" bg={traditionalBg} borderColor={borderColor}>
                  <HStack spacing={2}>
                    <Text>Традиционный подход</Text>
                    <Badge colorScheme="gray" fontSize="xs">Offline</Badge>
                  </HStack>
                </Th>
              </Tr>
            </Thead>
            <Tbody>
              {comparisonData.map((item, index) => (
                <Tr 
                  key={index}
                  bg={hoveredRow === index ? hoverBg : 'transparent'}
                  transition="all 0.3s ease"
                  onMouseEnter={() => setHoveredRow(index)}
                  onMouseLeave={() => setHoveredRow(null)}
                  opacity={isTableVisible ? 1 : 0}
                  transform={isTableVisible ? "translateY(0)" : "translateY(20px)"}
                  style={{ 
                    transition: `opacity 0.5s ease ${index * 0.1}s, transform 0.5s ease ${index * 0.1}s`,
                    cursor: 'pointer'
                  }}
                >
                  <Td 
                    fontWeight="bold" 
                    borderColor={borderColor}
                  >
                    {item.parameter}
                  </Td>
                  <Td 
                    fontSize="sm" 
                    color="gray.600" 
                    borderColor={borderColor}
                  >
                    {item.description}
                  </Td>
                  <Td 
                    bg={psybalansBg} 
                    borderColor={borderColor}
                  >
                    <Tooltip label={item.psybalans.details} placement="top">
                      <VStack align="start" spacing={1}>
                        <Text fontWeight="medium">{item.psybalans.value}</Text>
                        {renderRatingBadge(item.psybalans.rating)}
                      </VStack>
                    </Tooltip>
                  </Td>
                  <Td 
                    bg={traditionalBg} 
                    borderColor={borderColor}
                  >
                    <Tooltip label={item.traditional.details} placement="top">
                      <VStack align="start" spacing={1}>
                        <Text fontWeight="medium">{item.traditional.value}</Text>
                        {renderRatingBadge(item.traditional.rating)}
                      </VStack>
                    </Tooltip>
                  </Td>
                </Tr>
              ))}
            </Tbody>
          </Table>
        </Box>
      )}
      
      <Text fontSize="sm" color="gray.500" mt={4} textAlign="center">
        * Данные основаны на сравнительных исследованиях цифровых и традиционных подходов в психологии
      </Text>
    </Box>
  );
};

export default ComparisonTable;