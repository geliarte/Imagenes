#!/usr/bin/env python3
"""
Optimizador de imágenes para web
Optimiza imágenes JPG y PNG en el directorio actual manteniendo calidad visual
"""

import os
import sys
import argparse
from pathlib import Path
from PIL import Image, ImageOps

class ImageOptimizer:
    def __init__(self, quality=85, max_width=1920, max_height=1080, progressive=True):
        self.quality = quality
        self.max_width = max_width
        self.max_height = max_height
        self.progressive = progressive
        self.supported_formats = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.tiff'}
        self.stats = {
            'processed': 0,
            'skipped': 0,
            'errors': 0,
            'original_size': 0,
            'optimized_size': 0
        }

    def is_image_file(self, filepath):
        """Verifica si el archivo es una imagen soportada"""
        return filepath.suffix.lower() in self.supported_formats

    def get_output_format(self, input_path):
        """Determina el formato de salida basado en el archivo de entrada"""
        ext = input_path.suffix.lower()
        if ext in {'.jpg', '.jpeg', '.bmp', '.tiff'}:
            return 'JPEG'
        elif ext == '.png':
            return 'PNG'
        elif ext == '.webp':
            return 'WEBP'
        else:
            return 'JPEG'  # Por defecto

    def optimize_image(self, input_path, output_path=None, backup=False):
        """Optimiza una imagen individual"""
        try:
            # Si no se especifica output_path, sobreescribe el original
            if output_path is None:
                output_path = input_path
            
            # Crear backup si se solicita
            if backup and output_path == input_path:
                backup_path = input_path.with_suffix(f'.backup{input_path.suffix}')
                if not backup_path.exists():
                    os.rename(input_path, backup_path)
                    input_path = backup_path

            # Obtener tamaño original
            original_size = os.path.getsize(input_path)
            self.stats['original_size'] += original_size

            # Abrir y procesar imagen
            with Image.open(input_path) as img:
                # Convertir a RGB si es necesario para JPEG
                output_format = self.get_output_format(input_path)
                if output_format == 'JPEG' and img.mode in ('RGBA', 'LA', 'P'):
                    # Crear fondo blanco para transparencias
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    background.paste(img, mask=img.split()[-1] if img.mode == 'RGBA' else None)
                    img = background

                # Redimensionar si es necesario
                if img.width > self.max_width or img.height > self.max_height:
                    img.thumbnail((self.max_width, self.max_height), Image.Resampling.LANCZOS)

                # Aplicar orientación EXIF
                img = ImageOps.exif_transpose(img)

                # Configurar parámetros de guardado
                save_kwargs = {'optimize': True}
                
                if output_format == 'JPEG':
                    save_kwargs.update({
                        'quality': self.quality,
                        'progressive': self.progressive,
                        'format': 'JPEG'
                    })
                    # Cambiar extensión a .jpg si es necesario
                    if output_path.suffix.lower() not in {'.jpg', '.jpeg'}:
                        output_path = output_path.with_suffix('.jpg')
                
                elif output_format == 'PNG':
                    save_kwargs.update({
                        'optimize': True,
                        'format': 'PNG'
                    })
                
                elif output_format == 'WEBP':
                    save_kwargs.update({
                        'quality': self.quality,
                        'method': 6,  # Mejor compresión
                        'format': 'WEBP'
                    })

                # Guardar imagen optimizada
                img.save(output_path, **save_kwargs)

            # Actualizar estadísticas
            optimized_size = os.path.getsize(output_path)
            self.stats['optimized_size'] += optimized_size
            self.stats['processed'] += 1

            # Mostrar resultado
            reduction = ((original_size - optimized_size) / original_size) * 100
            print(f"✓ {input_path.name} -> {self.format_size(original_size)} -> {self.format_size(optimized_size)} ({reduction:+.1f}%)")

            return True

        except Exception as e:
            print(f"✗ Error procesando {input_path.name}: {str(e)}")
            self.stats['errors'] += 1
            return False

    def format_size(self, size_bytes):
        """Formatea el tamaño en bytes a una representación legible"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"

    def optimize_directory(self, directory_path, recursive=False, backup=False, output_dir=None):
        """Optimiza todas las imágenes en un directorio"""
        directory = Path(directory_path)
        
        if not directory.exists():
            print(f"Error: El directorio {directory_path} no existe")
            return False

        # Crear directorio de salida si se especifica
        if output_dir:
            output_directory = Path(output_dir)
            output_directory.mkdir(parents=True, exist_ok=True)

        # Buscar archivos de imagen
        pattern = "**/*" if recursive else "*"
        image_files = [f for f in directory.glob(pattern) 
                      if f.is_file() and self.is_image_file(f)]

        if not image_files:
            print("No se encontraron archivos de imagen en el directorio")
            return False

        print(f"Encontradas {len(image_files)} imágenes para optimizar")
        print("-" * 60)

        # Procesar cada imagen
        for image_file in image_files:
            if output_dir:
                # Mantener estructura de directorios en el output
                relative_path = image_file.relative_to(directory)
                output_path = output_directory / relative_path
                output_path.parent.mkdir(parents=True, exist_ok=True)
            else:
                output_path = None

            success = self.optimize_image(image_file, output_path, backup)
            
            if not success:
                self.stats['skipped'] += 1

        # Mostrar estadísticas finales
        self.print_summary()
        return True

    def print_summary(self):
        """Imprime un resumen de la optimización"""
        print("-" * 60)
        print("RESUMEN DE OPTIMIZACIÓN:")
        print(f"Imágenes procesadas: {self.stats['processed']}")
        print(f"Imágenes con errores: {self.stats['errors']}")
        print(f"Tamaño original total: {self.format_size(self.stats['original_size'])}")
        print(f"Tamaño optimizado total: {self.format_size(self.stats['optimized_size'])}")
        
        if self.stats['original_size'] > 0:
            total_reduction = ((self.stats['original_size'] - self.stats['optimized_size']) 
                             / self.stats['original_size']) * 100
            saved_space = self.stats['original_size'] - self.stats['optimized_size']
            print(f"Espacio ahorrado: {self.format_size(saved_space)} ({total_reduction:.1f}%)")


def main():
    parser = argparse.ArgumentParser(
        description="Optimiza imágenes para web manteniendo calidad visual",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Ejemplos de uso:
  python image_optimizer.py                    # Optimiza imágenes en directorio actual
  python image_optimizer.py -r                # Incluye subdirectorios
  python image_optimizer.py -q 90             # Calidad JPEG 90%
  python image_optimizer.py --backup          # Crea respaldos de originales
  python image_optimizer.py -o optimized/     # Guarda en directorio específico
  python image_optimizer.py --max-size 1200   # Redimensiona a máximo 1200px
        """
    )
    
    parser.add_argument('-d', '--directory', 
                       default='.', 
                       help='Directorio a procesar (por defecto: directorio actual)')
    
    parser.add_argument('-r', '--recursive', 
                       action='store_true',
                       help='Procesar subdirectorios recursivamente')
    
    parser.add_argument('-q', '--quality', 
                       type=int, 
                       default=85,
                       help='Calidad JPEG (1-100, por defecto: 85)')
    
    parser.add_argument('--max-width', 
                       type=int, 
                       default=1920,
                       help='Ancho máximo en píxeles (por defecto: 1920)')
    
    parser.add_argument('--max-height', 
                       type=int, 
                       default=1080,
                       help='Alto máximo en píxeles (por defecto: 1080)')
    
    parser.add_argument('--max-size', 
                       type=int,
                       help='Tamaño máximo (aplicado a width y height)')
    
    parser.add_argument('--backup', 
                       action='store_true',
                       help='Crear respaldo de archivos originales')
    
    parser.add_argument('-o', '--output', 
                       help='Directorio de salida (por defecto: sobreescribe originales)')
    
    parser.add_argument('--no-progressive', 
                       action='store_true',
                       help='Deshabilitar JPEG progresivo')

    args = parser.parse_args()

    # Validar argumentos
    if args.quality < 1 or args.quality > 100:
        print("Error: La calidad debe estar entre 1 y 100")
        sys.exit(1)

    # Aplicar max-size si se especifica
    if args.max_size:
        args.max_width = args.max_size
        args.max_height = args.max_size

    # Crear optimizador
    optimizer = ImageOptimizer(
        quality=args.quality,
        max_width=args.max_width,
        max_height=args.max_height,
        progressive=not args.no_progressive
    )

    # Mostrar configuración
    print("CONFIGURACIÓN DE OPTIMIZACIÓN:")
    print(f"Directorio: {args.directory}")
    print(f"Recursivo: {'Sí' if args.recursive else 'No'}")
    print(f"Calidad JPEG: {args.quality}%")
    print(f"Tamaño máximo: {args.max_width}x{args.max_height}px")
    print(f"JPEG progresivo: {'No' if args.no_progressive else 'Sí'}")
    print(f"Crear respaldos: {'Sí' if args.backup else 'No'}")
    if args.output:
        print(f"Directorio de salida: {args.output}")
    print("=" * 60)

    # Ejecutar optimización
    try:
        success = optimizer.optimize_directory(
            args.directory, 
            recursive=args.recursive,
            backup=args.backup,
            output_dir=args.output
        )
        
        if success:
            print("\n¡Optimización completada exitosamente!")
        else:
            print("\nLa optimización no se pudo completar")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\nOptimización interrumpida por el usuario")
        sys.exit(1)
    except Exception as e:
        print(f"\nError inesperado: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
