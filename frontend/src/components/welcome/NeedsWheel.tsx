import React, { useState } from 'react';
import { Box, Tooltip, useColorModeValue } from '@chakra-ui/react';
import { keyframes } from '@emotion/react';

// Типы данных для секторов колеса
interface NeedSector {
  id: string;
  name: string;
  description: string;
  color: string;
  path: string; // SVG path для сектора
  angle: number; // угол для анимации и расположения
}

// Свойства компонента колеса
interface NeedsWheelProps {
  onSectorClick?: (sectorId: string) => void;
  size?: number;
  className?: string;
}

// Анимация пульсации для активного сектора
const pulse = keyframes`
  0% { transform: scale(1); opacity: 0.8; }
  50% { transform: scale(1.05); opacity: 1; }
  100% { transform: scale(1); opacity: 0.8; }
`;

// Анимация появления колеса
const rotateIn = keyframes`
  0% { transform: rotate(-30deg) scale(0.8); opacity: 0; }
  100% { transform: rotate(0) scale(1); opacity: 1; }
`;

// Основной компонент колеса потребностей
const NeedsWheel: React.FC<NeedsWheelProps> = ({ 
  onSectorClick, 
  size = 280,
  className 
}) => {
  // Определяем сектора колеса потребностей
  const sectors: NeedSector[] = [
    {
      id: 'physical',
      name: 'Физические',
      description: 'Потребности тела: сон, питание, движение, отдых',
      color: 'var(--physical-need, #48BB78)',
      path: 'M 140,140 L 140,0 A 140,140 0 0,1 230,80 z',
      angle: 0
    },
    {
      id: 'emotional',
      name: 'Эмоциональные',
      description: 'Эмоциональное благополучие: радость, спокойствие, уверенность',
      color: 'var(--emotional-need, #ED8936)',
      path: 'M 140,140 L 230,80 A 140,140 0 0,1 190,240 z',
      angle: 72
    },
    {
      id: 'social',
      name: 'Социальные',
      description: 'Связь с другими людьми: общение, принадлежность, признание',
      color: 'var(--social-need, #4299E1)',
      path: 'M 140,140 L 190,240 A 140,140 0 0,1 50,200 z',
      angle: 144
    },
    {
      id: 'cognitive',
      name: 'Когнитивные',
      description: 'Интеллектуальное развитие: познание, обучение, творчество',
      color: 'var(--cognitive-need, #805AD5)',
      path: 'M 140,140 L 50,200 A 140,140 0 0,1 30,60 z',
      angle: 216
    },
    {
      id: 'spiritual',
      name: 'Духовные',
      description: 'Ценности и смыслы: осознанность, гармония, предназначение',
      color: 'var(--spiritual-need, #DD6B20)',
      path: 'M 140,140 L 30,60 A 140,140 0 0,1 140,0 z',
      angle: 288
    }
  ];

  // Стейт для активного сектора
  const [activeSector, setActiveSector] = useState<string | null>(null);

  // Обработчик наведения на сектор
  const handleMouseEnter = (sectorId: string) => {
    setActiveSector(sectorId);
  };

  // Обработчик ухода мыши с сектора
  const handleMouseLeave = () => {
    setActiveSector(null);
  };

  // Обработчик клика по сектору
  const handleClick = (sectorId: string) => {
    if (onSectorClick) {
      onSectorClick(sectorId);
    }
  };
  
  // Обработчик клавиатурных событий для доступности
  const handleKeyDown = (e: React.KeyboardEvent, sectorId: string) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      handleClick(sectorId);
    }
  };

  // Теневой эффект для колеса
  const wheelShadow = useColorModeValue(
    '0 10px 30px rgba(0, 0, 0, 0.1)', 
    '0 10px 30px rgba(0, 0, 0, 0.3)'
  );

  return (
    <Box 
      className={`needs-wheel ${className || ''}`}
      position="relative"
      width={`${size}px`}
      height={`${size}px`}
      margin="0 auto"
      animation={`${rotateIn} 1s ease-out forwards`}
      boxShadow={wheelShadow}
      borderRadius="50%"
      role="group"
      aria-label="Колесо психологических потребностей"
    >
      <svg 
        width={size} 
        height={size} 
        viewBox="0 0 280 280"
        style={{ 
          filter: 'drop-shadow(0px 4px 6px rgba(0, 0, 0, 0.1))',
          borderRadius: '50%',
        }}
      >
        {/* Центральный круг */}
        <circle
          cx="140"
          cy="140"
          r="40"
          fill="white"
          stroke="rgba(0,0,0,0.1)"
          strokeWidth="1"
          filter="drop-shadow(0px 2px 3px rgba(0, 0, 0, 0.1))"
        />
        
        {/* Иконка в центре */}
        <text
          x="140"
          y="140"
          fontSize="30"
          textAnchor="middle"
          dominantBaseline="middle"
          fill="#718096"
        >
          ⚖️
        </text>
        
        {/* Сектора колеса */}
        {sectors.map((sector) => (
          <Tooltip
            key={sector.id}
            label={`${sector.name}: ${sector.description}`}
            aria-label={`${sector.name}: ${sector.description}`}
            placement="auto"
            hasArrow
          >
            <g>
              <path
                d={sector.path}
                fill={sector.color}
                stroke="white"
                strokeWidth="2"
                opacity={activeSector === sector.id ? 1 : 0.8}
                cursor="pointer"
                transform={activeSector === sector.id ? 'scale(1.03)' : 'scale(1)'}
                transformOrigin="center"
                transition="all 0.3s ease"
                animation={activeSector === sector.id ? `${pulse} 2s infinite` : 'none'}
                aria-label={sector.name}
                tabIndex={0}
                role="button"
                onMouseEnter={() => handleMouseEnter(sector.id)}
                onMouseLeave={handleMouseLeave}
                onClick={() => handleClick(sector.id)}
                onKeyDown={(e) => handleKeyDown(e, sector.id)}
              />
              
              {/* Текст для каждого сектора */}
              <text
                fontSize="12"
                fontWeight="bold"
                fill="white"
                textAnchor="middle"
                transform={`rotate(${sector.angle} 140 140) translate(110, 0)`}
              >
                {sector.name}
              </text>
            </g>
          </Tooltip>
        ))}
      </svg>
    </Box>
  );
};

export default NeedsWheel;