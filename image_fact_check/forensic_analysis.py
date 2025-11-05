"""
Advanced Image Forensic Analysis Module
Detects even the smallest Photoshop edits using multiple forensic techniques
"""

import numpy as np
import warnings
import random
from PIL import Image
from io import BytesIO
from typing import Dict, Tuple, List, Optional
import cv2
from scipy import ndimage, stats
from scipy.signal import correlate2d
from scipy.fft import fft2, fftshift
import math

# Suppress numpy warnings for empty slices (we handle them explicitly)
warnings.filterwarnings('ignore', category=RuntimeWarning, module='numpy')


def error_level_analysis(image: np.ndarray, quality: int = 95) -> Dict[str, float]:
    """
    Error Level Analysis (ELA) - Detects compression inconsistencies
    
    Even subtle edits leave traces in compression artifacts.
    Re-saved regions have different error levels than original regions.
    """
    try:
        # Convert to RGB if needed
        if len(image.shape) == 3:
            # Convert to grayscale for ELA
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Save image at specific quality and reload
        buffer = BytesIO()
        pil_img = Image.fromarray(gray)
        pil_img.save(buffer, format='JPEG', quality=quality)
        buffer.seek(0)
        recompressed = np.array(Image.open(buffer))
        
        # Calculate error level
        ela = np.abs(gray.astype(np.float32) - recompressed.astype(np.float32))
        
        # Analyze ELA statistics
        ela_mean = np.mean(ela)
        ela_std = np.std(ela)
        ela_max = np.max(ela)
        ela_median = np.median(ela)
        
        # Calculate coefficient of variation (high variance = inconsistent compression = editing)
        cv_score = ela_std / (ela_mean + 1e-10)
        
        # Check for regions with unusually high error levels (edited regions)
        # Split into 9 regions (3x3 grid)
        h, w = ela.shape
        regions = []
        for i in range(3):
            for j in range(3):
                y1, y2 = i * h // 3, (i + 1) * h // 3
                x1, x2 = j * w // 3, (j + 1) * w // 3
                region_ela = ela[y1:y2, x1:x2]
                regions.append({
                    'mean': np.mean(region_ela),
                    'std': np.std(region_ela),
                    'max': np.max(region_ela)
                })
        
        # Calculate variance between regions
        region_means = [r['mean'] for r in regions]
        region_variance = np.var(region_means)
        region_mean_std = np.std(region_means)
        
        # High variance between regions = inconsistent compression = editing
        inconsistency_score = region_variance / (np.mean(region_means) + 1e-10)
        
        # Detect outliers (regions with significantly different error levels)
        outlier_count = 0
        if len(region_means) > 1:
            mean_all = np.mean(region_means)
            std_all = np.std(region_means)
            for r_mean in region_means:
                if abs(r_mean - mean_all) > 2 * std_all:  # 2 sigma rule
                    outlier_count += 1
        
        # More sensitive thresholds for detecting even tiny edits
        return {
            'ela_mean': float(ela_mean),
            'ela_std': float(ela_std),
            'ela_cv': float(cv_score),
            'inconsistency_score': float(inconsistency_score),
            'outlier_regions': int(outlier_count),
            'suspicious': inconsistency_score > 0.15 or outlier_count >= 1 or cv_score > 0.3  # Much more sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def noise_pattern_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Noise Pattern Analysis - Detects inconsistencies in noise patterns
    
    Original images have consistent noise patterns. Edited regions often have
    different noise characteristics.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Apply high-pass filter to extract noise
        kernel = np.array([[-1, -1, -1],
                          [-1,  8, -1],
                          [-1, -1, -1]]) / 9.0
        noise = cv2.filter2D(gray.astype(np.float32), -1, kernel)
        
        # Analyze noise statistics in different regions
        h, w = noise.shape
        regions = []
        for i in range(4):
            for j in range(4):
                y1, y2 = i * h // 4, (i + 1) * h // 4
                x1, x2 = j * w // 4, (j + 1) * w // 4
                region_noise = noise[y1:y2, x1:x2]
                regions.append({
                    'mean': float(np.mean(region_noise)),
                    'std': float(np.std(region_noise)),
                    'variance': float(np.var(region_noise))
                })
        
        # Calculate variance between regions
        noise_means = [r['mean'] for r in regions]
        noise_stds = [r['std'] for r in regions]
        
        mean_variance = np.var(noise_means)
        std_variance = np.var(noise_stds)
        
        # Calculate coefficient of variation for noise
        noise_cv = np.std(noise_stds) / (np.mean(noise_stds) + 1e-10)
        
        # Check for regions with significantly different noise patterns
        outlier_count = 0
        if len(noise_stds) > 1:
            mean_std = np.mean(noise_stds)
            std_std = np.std(noise_stds)
            for ns in noise_stds:
                if abs(ns - mean_std) > 2 * std_std:
                    outlier_count += 1
        
        # More sensitive thresholds
        return {
            'noise_variance': float(mean_variance),
            'noise_std_variance': float(std_variance),
            'noise_cv': float(noise_cv),
            'outlier_regions': int(outlier_count),
            'suspicious': noise_cv > 0.25 or outlier_count >= 1 or mean_variance > 50  # Much more sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def copy_move_detection(image: np.ndarray, block_size: int = 16) -> Dict[str, float]:
    """
    Copy-Move Detection - Detects duplicated regions (clone stamp usage)
    
    Uses block-based analysis to find identical or near-identical regions.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        
        # For very large images, use larger step size to reduce computation
        # Adaptive block size based on image size
        if h * w > 2000000:  # For images larger than ~2MP
            step_size = block_size  # Non-overlapping for speed
        else:
            step_size = block_size // 2  # Overlapping for accuracy
        
        # Divide image into blocks
        blocks = []
        block_coords = []
        
        for y in range(0, h - block_size, step_size):
            for x in range(0, w - block_size, step_size):
                block = gray[y:y+block_size, x:x+block_size]
                if block.shape == (block_size, block_size):
                    blocks.append(block.flatten())
                    block_coords.append((y, x))
        
        if len(blocks) < 4:
            return {'suspicious': False, 'duplicate_blocks': 0}
        
        blocks_array = np.array(blocks)
        
        # Calculate similarity between blocks using correlation
        # Use a faster approach: compare blocks using mean and std
        block_features = []
        for block in blocks:
            block_features.append([np.mean(block), np.std(block)])
        
        features_array = np.array(block_features)
        
        # Find similar blocks using distance threshold
        # For large images, limit comparisons to prevent excessive computation
        similarity_threshold = 5.0  # Threshold for similarity
        duplicate_pairs = []
        max_comparisons = 50000  # Limit comparisons for large images
        
        total_comparisons = len(features_array) * (len(features_array) - 1) // 2
        if total_comparisons > max_comparisons:
            # Sample blocks for comparison to speed up processing
            import random
            sample_size = int(np.sqrt(max_comparisons * 2))
            if sample_size < len(features_array):
                indices = random.sample(range(len(features_array)), min(sample_size, len(features_array)))
                indices.sort()
            else:
                indices = list(range(len(features_array)))
        else:
            indices = list(range(len(features_array)))
        
        for idx_i, i in enumerate(indices):
            for j in indices[idx_i + 1:]:
                dist = np.linalg.norm(features_array[i] - features_array[j])
                if dist < similarity_threshold:
                    # Check spatial distance (duplicates far apart = suspicious)
                    y1, x1 = block_coords[i]
                    y2, x2 = block_coords[j]
                    spatial_dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    
                    # If blocks are similar but far apart, likely copy-move
                    if spatial_dist > block_size * 3:
                        duplicate_pairs.append((i, j, spatial_dist))
        
        duplicate_score = len(duplicate_pairs) / max(len(blocks) // 10, 1)
        
        # More sensitive: detect even small duplicate regions
        return {
            'duplicate_pairs': len(duplicate_pairs),
            'duplicate_score': float(duplicate_score),
            'suspicious': len(duplicate_pairs) > 2 or duplicate_score > 0.05  # Much more sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def luminance_gradient_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Luminance Gradient Analysis - Detects unnatural lighting patterns
    
    Original photos have consistent lighting gradients. Edited regions often
    have abrupt or inconsistent gradients.
    """
    try:
        if len(image.shape) == 3:
            # Convert to LAB color space and use L channel
            lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
            luminance = lab[:, :, 0]
        else:
            luminance = image.copy()
        
        # Calculate gradients
        grad_x = cv2.Sobel(luminance, cv2.CV_64F, 1, 0, ksize=3)
        grad_y = cv2.Sobel(luminance, cv2.CV_64F, 0, 1, ksize=3)
        gradient_magnitude = np.sqrt(grad_x**2 + grad_y**2)
        
        # Analyze gradient consistency across regions
        h, w = gradient_magnitude.shape
        regions = []
        
        for i in range(3):
            for j in range(3):
                y1, y2 = i * h // 3, (i + 1) * h // 3
                x1, x2 = j * w // 3, (j + 1) * w // 3
                region_grad = gradient_magnitude[y1:y2, x1:x2]
                regions.append({
                    'mean': float(np.mean(region_grad)),
                    'std': float(np.std(region_grad)),
                    'max': float(np.max(region_grad))
                })
        
        # Calculate variance between regions
        grad_means = [r['mean'] for r in regions]
        grad_stds = [r['std'] for r in regions]
        
        mean_variance = np.var(grad_means)
        std_variance = np.var(grad_stds)
        
        # High variance = inconsistent gradients = editing
        inconsistency_score = mean_variance / (np.mean(grad_means) + 1e-10)
        
        # Detect abrupt transitions (high gradient concentration)
        gradient_threshold = np.percentile(gradient_magnitude, 95)
        abrupt_transitions = np.sum(gradient_magnitude > gradient_threshold)
        abrupt_ratio = abrupt_transitions / (h * w)
        
        # More sensitive thresholds
        return {
            'gradient_variance': float(mean_variance),
            'gradient_inconsistency': float(inconsistency_score),
            'abrupt_transitions': int(abrupt_transitions),
            'abrupt_ratio': float(abrupt_ratio),
            'suspicious': inconsistency_score > 0.25 or abrupt_ratio > 0.03  # Much more sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def color_consistency_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Color Consistency Analysis - Detects color temperature and white balance inconsistencies
    
    Edited regions often have different color temperatures or white balance.
    """
    try:
        # Convert to LAB color space for better color analysis
        lab = cv2.cvtColor(image, cv2.COLOR_RGB2LAB)
        
        # Extract A and B channels (color information)
        a_channel = lab[:, :, 1]
        b_channel = lab[:, :, 2]
        
        # Analyze color consistency across regions
        h, w = a_channel.shape
        regions = []
        
        for i in range(4):
            for j in range(4):
                y1, y2 = i * h // 4, (i + 1) * h // 4
                x1, x2 = j * w // 4, (j + 1) * w // 4
                
                region_a = a_channel[y1:y2, x1:x2]
                region_b = b_channel[y1:y2, x1:x2]
                
                # Calculate color temperature indicators
                # A channel: green-red axis, B channel: blue-yellow axis
                mean_a = np.mean(region_a)
                mean_b = np.mean(region_b)
                std_a = np.std(region_a)
                std_b = np.std(region_b)
                
                regions.append({
                    'mean_a': float(mean_a),
                    'mean_b': float(mean_b),
                    'std_a': float(std_a),
                    'std_b': float(std_b)
                })
        
        # Calculate variance in color temperature
        mean_a_values = [r['mean_a'] for r in regions]
        mean_b_values = [r['mean_b'] for r in regions]
        
        a_variance = np.var(mean_a_values)
        b_variance = np.var(mean_b_values)
        
        # Calculate color temperature difference
        color_temp_variance = np.sqrt(a_variance**2 + b_variance**2)
        
        # Detect outliers (regions with significantly different colors)
        outlier_count = 0
        if len(mean_a_values) > 1:
            mean_a_all = np.mean(mean_a_values)
            std_a_all = np.std(mean_a_values)
            mean_b_all = np.mean(mean_b_values)
            std_b_all = np.std(mean_b_values)
            
            for i in range(len(mean_a_values)):
                dist_a = abs(mean_a_values[i] - mean_a_all)
                dist_b = abs(mean_b_values[i] - mean_b_all)
                if dist_a > 2 * std_a_all or dist_b > 2 * std_b_all:
                    outlier_count += 1
        
        # More sensitive thresholds - detect even tiny color differences
        return {
            'color_temp_variance': float(color_temp_variance),
            'a_channel_variance': float(a_variance),
            'b_channel_variance': float(b_variance),
            'outlier_regions': int(outlier_count),
            'suspicious': color_temp_variance > 50 or outlier_count >= 1  # Much more sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def edge_quality_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Edge Quality Analysis - Detects unnaturally perfect edges
    
    Edited regions often have edges that are too perfect or inconsistent
    with the rest of the image.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Detect edges using Canny
        edges = cv2.Canny(gray, 50, 150)
        
        # Calculate edge density in different regions
        h, w = edges.shape
        regions = []
        
        for i in range(4):
            for j in range(4):
                y1, y2 = i * h // 4, (i + 1) * h // 4
                x1, x2 = j * w // 4, (j + 1) * w // 4
                region_edges = edges[y1:y2, x1:x2]
                edge_density = np.sum(region_edges > 0) / (region_edges.size + 1e-10)
                
                # Calculate edge smoothness (perfect edges have high smoothness)
                if np.sum(region_edges) > 0:
                    # Use gradient of edges to measure smoothness
                    edge_grad = cv2.Sobel(region_edges.astype(np.float32), cv2.CV_64F, 1, 1, ksize=3)
                    edge_smoothness = 1.0 / (np.std(edge_grad) + 1e-10)
                else:
                    edge_smoothness = 0
                
                regions.append({
                    'density': float(edge_density),
                    'smoothness': float(edge_smoothness)
                })
        
        # Analyze edge consistency
        densities = [r['density'] for r in regions]
        smoothnesses = [r['smoothness'] for r in regions]
        
        density_variance = np.var(densities)
        smoothness_variance = np.var(smoothnesses)
        
        # High smoothness variance = inconsistent edge quality = editing
        # Very high smoothness = unnaturally perfect edges = editing
        max_smoothness = max(smoothnesses) if smoothnesses else 0
        avg_smoothness = np.mean(smoothnesses)
        
        # More sensitive thresholds
        return {
            'edge_density_variance': float(density_variance),
            'edge_smoothness_variance': float(smoothness_variance),
            'max_smoothness': float(max_smoothness),
            'avg_smoothness': float(avg_smoothness),
            'suspicious': smoothness_variance > 500 or max_smoothness > 3000 or density_variance > 0.0005  # Much more sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def frequency_domain_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Frequency Domain Analysis (FFT) - Detects editing artifacts in frequency domain
    
    Edited regions often have unnatural frequency patterns, especially 
    when content-aware fill or clone tools are used.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        # Apply FFT
        f_transform = fft2(gray.astype(np.float32))
        f_shift = fftshift(f_transform)
        magnitude_spectrum = np.abs(f_shift)
        
        # Analyze frequency patterns in different regions
        h, w = magnitude_spectrum.shape
        regions = []
        
        # Divide frequency domain into regions
        for i in range(4):
            for j in range(4):
                y1, y2 = i * h // 4, (i + 1) * h // 4
                x1, x2 = j * w // 4, (j + 1) * w // 4
                region_freq = magnitude_spectrum[y1:y2, x1:x2]
                regions.append({
                    'mean': float(np.mean(region_freq)),
                    'std': float(np.std(region_freq)),
                    'max': float(np.max(region_freq)),
                    'median': float(np.median(region_freq))
                })
        
        # Calculate variance between regions
        freq_means = [r['mean'] for r in regions]
        freq_stds = [r['std'] for r in regions]
        
        mean_variance = np.var(freq_means)
        std_variance = np.var(freq_stds)
        
        # High variance = inconsistent frequency patterns = editing
        inconsistency_score = mean_variance / (np.mean(freq_means) + 1e-10)
        
        # Detect outliers
        outlier_count = 0
        if len(freq_means) > 1:
            mean_all = np.mean(freq_means)
            std_all = np.std(freq_means)
            for f_mean in freq_means:
                if abs(f_mean - mean_all) > 1.5 * std_all:  # More sensitive threshold
                    outlier_count += 1
        
        return {
            'freq_variance': float(mean_variance),
            'freq_std_variance': float(std_variance),
            'freq_inconsistency': float(inconsistency_score),
            'outlier_regions': int(outlier_count),
            'suspicious': inconsistency_score > 0.2 or outlier_count >= 1 or std_variance > 1000
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def statistical_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Higher-Order Statistical Analysis - Detects micro-edits using statistics
    
    Uses skewness, kurtosis, and other statistical measures to detect
    subtle inconsistencies that indicate editing.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        regions = []
        
        # Analyze small overlapping regions for micro-edits
        block_size = min(h // 8, w // 8, 64)
        if block_size < 4:
            return {'suspicious': False}
        step = max(block_size // 2, 1)
        
        for y in range(0, h - block_size, step):
            for x in range(0, w - block_size, step):
                region = gray[y:y+block_size, x:x+block_size]
                
                # Skip if region is too small or empty
                if region.size == 0:
                    continue
                
                region_flat = region.flatten()
                if len(region_flat) == 0:
                    continue
                
                # Calculate higher-order statistics with error handling
                try:
                    skew = stats.skew(region_flat) if len(region_flat) > 2 else 0.0
                    kurt = stats.kurtosis(region_flat) if len(region_flat) > 2 else 0.0
                    std = np.std(region) if region.size > 0 else 0.0
                    mean = np.mean(region) if region.size > 0 else 0.0
                except (ValueError, RuntimeWarning):
                    continue
                
                regions.append({
                    'mean': float(mean),
                    'std': float(std),
                    'skewness': float(skew),
                    'kurtosis': float(kurt)
                })
        
        if len(regions) < 4:
            return {'suspicious': False}
        
        # Analyze consistency of statistics across regions
        means = [r['mean'] for r in regions]
        stds = [r['std'] for r in regions]
        skews = [r['skewness'] for r in regions]
        kurtoses = [r['kurtosis'] for r in regions]
        
        # Calculate variance of statistics
        mean_variance = np.var(means)
        std_variance = np.var(stds)
        skew_variance = np.var(skews)
        kurt_variance = np.var(kurtoses)
        
        # Inconsistent statistics = editing
        total_variance = mean_variance + std_variance + skew_variance + kurt_variance
        
        # Detect outliers in each statistic
        outlier_count = 0
        for stat_list in [means, stds, skews, kurtoses]:
            if len(stat_list) > 1:
                try:
                    mean_stat = np.mean(stat_list)
                    std_stat = np.std(stat_list)
                    if std_stat > 0:  # Avoid division by zero
                        for val in stat_list:
                            if abs(val - mean_stat) > 1.5 * std_stat:
                                outlier_count += 1
                except (ValueError, RuntimeWarning):
                    continue
        
        return {
            'stat_variance': float(total_variance),
            'mean_variance': float(mean_variance),
            'std_variance': float(std_variance),
            'skew_variance': float(skew_variance),
            'kurt_variance': float(kurt_variance),
            'outlier_count': int(outlier_count),
            'suspicious': total_variance > 500 or outlier_count > len(regions) * 0.1
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def pixel_neighborhood_analysis(image: np.ndarray) -> Dict[str, float]:
    """
    Pixel Neighborhood Analysis - Detects micro-edits by analyzing pixel neighborhoods
    
    Even tiny edits affect the relationships between neighboring pixels.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        
        # Analyze neighborhood consistency
        # Compare each pixel's neighborhood with surrounding neighborhoods
        neighborhood_size = 5
        inconsistencies = []
        
        for y in range(neighborhood_size, h - neighborhood_size, neighborhood_size):
            for x in range(neighborhood_size, w - neighborhood_size, neighborhood_size):
                # Get center neighborhood
                center = gray[y-neighborhood_size//2:y+neighborhood_size//2+1,
                             x-neighborhood_size//2:x+neighborhood_size//2+1]
                
                # Get surrounding neighborhoods
                neighbors = []
                for dy in [-neighborhood_size, 0, neighborhood_size]:
                    for dx in [-neighborhood_size, 0, neighborhood_size]:
                        if dy == 0 and dx == 0:
                            continue
                        ny = y + dy
                        nx = x + dx
                        if (0 <= ny < h - neighborhood_size//2 and 
                            0 <= nx < w - neighborhood_size//2):
                            neighbor = gray[ny-neighborhood_size//2:ny+neighborhood_size//2+1,
                                           nx-neighborhood_size//2:nx+neighborhood_size//2+1]
                            neighbors.append(neighbor)
                
                if len(neighbors) > 0:
                    # Calculate mean of neighbors
                    neighbor_means = [np.mean(n) for n in neighbors if n.size > 0]
                    if len(neighbor_means) == 0 or center.size == 0:
                        continue
                    
                    neighbor_mean = np.mean(neighbor_means)
                    center_mean = np.mean(center)
                    
                    # Check if center differs significantly from neighbors
                    try:
                        neighbor_std = np.std(neighbor_means) if len(neighbor_means) > 1 else 0
                        diff = abs(center_mean - neighbor_mean)
                        if neighbor_std > 0 and diff > neighbor_std * 1.5:
                            inconsistencies.append(diff)
                    except (ValueError, RuntimeWarning):
                        continue
        
        inconsistency_score = np.mean(inconsistencies) if inconsistencies else 0
        inconsistency_count = len(inconsistencies)
        
        return {
            'inconsistency_score': float(inconsistency_score),
            'inconsistency_count': int(inconsistency_count),
            'suspicious': inconsistency_score > 5 or inconsistency_count > 10
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def advanced_copy_move_detection(image: np.ndarray) -> Dict[str, float]:
    """
    Advanced Copy-Move Detection using DCT (Discrete Cosine Transform)
    
    More sensitive than block-based approach, detects even rotated/transformed duplicates.
    OPTIMIZED for large images with adaptive sampling.
    """
    try:
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image.copy()
        
        h, w = gray.shape
        
        # For very large images, skip this expensive analysis or use faster method
        if h * w > 4000000:  # For images larger than 4MP (2000x2000)
            print("  ⚠️ Skipping advanced copy-move (too large, using basic copy-move instead)")
            return {'suspicious': False, 'duplicate_pairs': 0, 'skipped': True}
        
        block_size = 16
        
        # Adaptive step size based on image size
        if h * w > 2000000:  # For images larger than 2MP
            step_size = block_size  # Non-overlapping for speed
        else:
            step_size = block_size // 2  # Overlapping for accuracy
        
        # Extract DCT features from blocks
        blocks = []
        block_coords = []
        
        for y in range(0, h - block_size, step_size):
            for x in range(0, w - block_size, step_size):
                block = gray[y:y+block_size, x:x+block_size].astype(np.float32)
                
                # Apply DCT
                dct_block = cv2.dct(block)
                
                # Extract low-frequency coefficients (top-left 8x8)
                features = dct_block[:8, :8].flatten()
                blocks.append(features)
                block_coords.append((y, x))
        
        if len(blocks) < 4:
            return {'suspicious': False, 'duplicate_pairs': 0}
        
        blocks_array = np.array(blocks)
        
        # Find similar blocks using cosine similarity
        # Limit comparisons for performance
        duplicate_pairs = []
        similarity_threshold = 0.95  # Very high similarity
        max_comparisons = 30000  # Limit for DCT comparison (more expensive)
        
        total_comparisons = len(blocks_array) * (len(blocks_array) - 1) // 2
        if total_comparisons > max_comparisons:
            # Sample blocks for comparison
            sample_size = int(np.sqrt(max_comparisons * 2))
            if sample_size < len(blocks_array):
                indices = random.sample(range(len(blocks_array)), min(sample_size, len(blocks_array)))
                indices.sort()
            else:
                indices = list(range(len(blocks_array)))
        else:
            indices = list(range(len(blocks_array)))
        
        # Pre-compute norms for faster comparison
        norms = np.linalg.norm(blocks_array, axis=1)
        
        for idx_i, i in enumerate(indices):
            if norms[i] == 0:
                continue
            for j in indices[idx_i + 1:]:
                if norms[j] == 0:
                    continue
                
                # Cosine similarity (optimized)
                dot_product = np.dot(blocks_array[i], blocks_array[j])
                similarity = dot_product / (norms[i] * norms[j])
                
                if similarity > similarity_threshold:
                    # Check spatial distance
                    y1, x1 = block_coords[i]
                    y2, x2 = block_coords[j]
                    spatial_dist = np.sqrt((x2 - x1)**2 + (y2 - y1)**2)
                    
                    # If blocks are very similar but far apart, likely copy-move
                    if spatial_dist > block_size * 2:
                        duplicate_pairs.append((i, j, spatial_dist, similarity))
        
        duplicate_score = len(duplicate_pairs) / max(len(blocks) // 20, 1)
        
        return {
            'duplicate_pairs': len(duplicate_pairs),
            'duplicate_score': float(duplicate_score),
            'suspicious': len(duplicate_pairs) > 1 or duplicate_score > 0.02  # Very sensitive
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False}


def metadata_analysis(image_file) -> Dict[str, any]:
    """
    Metadata Analysis - Checks EXIF data for editing software traces
    """
    try:
        from PIL.ExifTags import TAGS
        
        # Reset file pointer
        image_file.seek(0)
        img = Image.open(image_file)
        
        exif_data = {}
        if hasattr(img, '_getexif') and img._getexif() is not None:
            exif = img._getexif()
            for tag_id, value in exif.items():
                tag = TAGS.get(tag_id, tag_id)
                exif_data[tag] = value
        
        # Check for editing software indicators
        software_indicators = []
        suspicious_software = ['photoshop', 'adobe', 'gimp', 'paint', 'editor']
        
        # Check Software tag
        software = exif_data.get('Software', '')
        if software:
            software_lower = software.lower()
            for indicator in suspicious_software:
                if indicator in software_lower:
                    software_indicators.append(software)
        
        # Check for multiple software entries (often indicates editing)
        if len(software_indicators) > 0:
            suspicious = True
        else:
            suspicious = False
        
        # Check for modification date inconsistencies
        datetime_original = exif_data.get('DateTimeOriginal', '')
        datetime_digitized = exif_data.get('DateTimeDigitized', '')
        datetime_modified = exif_data.get('DateTime', '')
        
        # If modification date exists but is different from original, might be edited
        if datetime_modified and datetime_original and datetime_modified != datetime_original:
            suspicious = True
        
        return {
            'has_exif': len(exif_data) > 0,
            'software': software_indicators,
            'exif_count': len(exif_data),
            'suspicious': suspicious
        }
    except Exception as e:
        return {'error': str(e), 'suspicious': False, 'has_exif': False}


def comprehensive_forensic_analysis(image_file) -> Dict[str, any]:
    """
    Comprehensive Forensic Analysis combining all techniques
    
    Returns a detailed analysis with confidence scores
    """
    try:
        # Read image
        image_file.seek(0)
        image_data = image_file.read()
        pil_image = Image.open(BytesIO(image_data))
        
        # Convert to RGB if necessary
        if pil_image.mode != 'RGB':
            pil_image = pil_image.convert('RGB')
        
        # RESIZE LARGE IMAGES BEFORE ANALYSIS to prevent memory issues and speed up processing
        # Large images are resized but forensic analysis can still detect edits effectively
        max_dimension = 4000  # Maximum dimension for forensic analysis (balance between accuracy and speed)
        original_size = (pil_image.width, pil_image.height)
        
        if pil_image.width > max_dimension or pil_image.height > max_dimension:
            print(f"⚠️ Large image detected ({pil_image.width}x{pil_image.height}). Resizing to max {max_dimension}px for faster analysis...")
            # Maintain aspect ratio
            ratio = min(max_dimension / pil_image.width, max_dimension / pil_image.height)
            new_size = (int(pil_image.width * ratio), int(pil_image.height * ratio))
            pil_image = pil_image.resize(new_size, Image.Resampling.LANCZOS)
            print(f"✅ Resized to {pil_image.width}x{pil_image.height}")
        
        # Convert to numpy array
        image_array = np.array(pil_image)
        
        # Free memory by deleting the PIL image
        del pil_image
        
        # Run all forensic analyses (including new advanced techniques)
        print("  Running ELA analysis...")
        ela_results = error_level_analysis(image_array)
        
        print("  Running noise pattern analysis...")
        noise_results = noise_pattern_analysis(image_array)
        
        print("  Running copy-move detection...")
        copy_move_results = copy_move_detection(image_array)
        
        print("  Running advanced copy-move detection...")
        # Skip advanced copy-move for very large images (too slow)
        image_size = image_array.shape[0] * image_array.shape[1]
        if image_size > 4000000:  # Skip if larger than 4MP
            print("  ⚠️ Skipping advanced copy-move (image too large)")
            advanced_copy_move_results = {'suspicious': False, 'duplicate_pairs': 0, 'skipped': True}
        else:
            advanced_copy_move_results = advanced_copy_move_detection(image_array)
        
        print("  Running luminance gradient analysis...")
        luminance_results = luminance_gradient_analysis(image_array)
        
        print("  Running color consistency analysis...")
        color_results = color_consistency_analysis(image_array)
        
        print("  Running edge quality analysis...")
        edge_results = edge_quality_analysis(image_array)
        
        print("  Running frequency domain analysis...")
        frequency_results = frequency_domain_analysis(image_array)
        
        print("  Running statistical analysis...")
        statistical_results = statistical_analysis(image_array)
        
        print("  Running neighborhood analysis...")
        neighborhood_results = pixel_neighborhood_analysis(image_array)
        
        # Reset file pointer for metadata analysis
        image_file.seek(0)
        metadata_results = metadata_analysis(image_file)
        
        # Clean up memory
        del image_array
        
        # Count suspicious indicators
        suspicious_count = 0
        total_checks = 0
        
        checks = [
            ('ELA', ela_results.get('suspicious', False)),
            ('Noise', noise_results.get('suspicious', False)),
            ('Copy-Move', copy_move_results.get('suspicious', False)),
            ('Advanced Copy-Move', advanced_copy_move_results.get('suspicious', False)),
            ('Luminance', luminance_results.get('suspicious', False)),
            ('Color', color_results.get('suspicious', False)),
            ('Edge', edge_results.get('suspicious', False)),
            ('Frequency Domain', frequency_results.get('suspicious', False)),
            ('Statistical Analysis', statistical_results.get('suspicious', False)),
            ('Neighborhood Analysis', neighborhood_results.get('suspicious', False)),
            ('Metadata', metadata_results.get('suspicious', False))
        ]
        
        for check_name, is_suspicious in checks:
            if 'error' not in str(ela_results) and 'error' not in str(noise_results):
                total_checks += 1
                if is_suspicious:
                    suspicious_count += 1
        
        # Calculate confidence score
        if total_checks > 0:
            suspicion_ratio = suspicious_count / total_checks
        else:
            suspicion_ratio = 0.0
        
        # Determine if image is likely edited
        # ULTRA STRICT: if ANY technique flags it, mark as suspicious
        # Even stricter: if multiple techniques flag it, very high confidence
        is_edited = suspicious_count > 0
        
        # Confidence calculation - more aggressive for detection
        if suspicious_count >= 5:
            confidence = 0.95  # Very high confidence
        elif suspicious_count >= 3:
            confidence = 0.85  # High confidence
        elif suspicious_count == 2:
            confidence = 0.7  # Medium-high confidence
        elif suspicious_count == 1:
            confidence = 0.6  # Medium confidence - still suspicious
        else:
            confidence = 0.4  # Low confidence (but still possible - assume edited)
        
        # Build detailed report
        detection_details = []
        if ela_results.get('suspicious'):
            detection_details.append(f"تحليل مستوى الخطأ (ELA): تم اكتشاف عدم اتساق في الضغط في {ela_results.get('outlier_regions', 0)} منطقة")
        if noise_results.get('suspicious'):
            detection_details.append(f"تحليل نمط الضوضاء: تم اكتشاف اختلافات في أنماط الضوضاء في {noise_results.get('outlier_regions', 0)} منطقة")
        if copy_move_results.get('suspicious'):
            detection_details.append(f"كشف النسخ واللصق: تم العثور على {copy_move_results.get('duplicate_pairs', 0)} زوج من المناطق المكررة")
        if advanced_copy_move_results.get('suspicious'):
            detection_details.append(f"كشف النسخ واللصق المتقدم: تم العثور على {advanced_copy_move_results.get('duplicate_pairs', 0)} زوج من المناطق المكررة باستخدام تحليل DCT")
        if luminance_results.get('suspicious'):
            detection_details.append("تحليل التدرج اللوني: تم اكتشاف عدم اتساق في الإضاءة")
        if color_results.get('suspicious'):
            detection_details.append(f"تحليل اتساق الألوان: تم اكتشاف اختلافات في درجة حرارة اللون في {color_results.get('outlier_regions', 0)} منطقة")
        if edge_results.get('suspicious'):
            detection_details.append("تحليل جودة الحواف: تم اكتشاف حواف غير طبيعية أو مثالية بشكل مفرط")
        if frequency_results.get('suspicious'):
            detection_details.append(f"تحليل المجال الترددي (FFT): تم اكتشاف أنماط ترددية غير طبيعية في {frequency_results.get('outlier_regions', 0)} منطقة")
        if statistical_results.get('suspicious'):
            detection_details.append(f"التحليل الإحصائي المتقدم: تم اكتشاف {statistical_results.get('outlier_count', 0)} منطقة بإحصائيات غير متسقة")
        if neighborhood_results.get('suspicious'):
            detection_details.append(f"تحليل الجوار: تم اكتشاف {neighborhood_results.get('inconsistency_count', 0)} منطقة بعلاقات جوار غير طبيعية")
        if metadata_results.get('suspicious'):
            detection_details.append(f"تحليل البيانات الوصفية: تم اكتشاف مؤشرات على برامج التعديل: {', '.join(metadata_results.get('software', []))}")
        
        return {
            'is_edited': is_edited,
            'confidence': confidence,
            'suspicious_count': suspicious_count,
            'total_checks': total_checks,
            'suspicion_ratio': suspicion_ratio,
            'detection_details': detection_details,
            'detailed_results': {
                'ela': ela_results,
                'noise': noise_results,
                'copy_move': copy_move_results,
                'advanced_copy_move': advanced_copy_move_results,
                'luminance': luminance_results,
                'color': color_results,
                'edge': edge_results,
                'frequency': frequency_results,
                'statistical': statistical_results,
                'neighborhood': neighborhood_results,
                'metadata': metadata_results
            }
        }
    except Exception as e:
        return {
            'is_edited': False,
            'confidence': 0.0,
            'error': str(e),
            'detection_details': []
        }

