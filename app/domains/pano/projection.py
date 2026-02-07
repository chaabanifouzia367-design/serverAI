"""
Panoramic Projection Module

Generates a synthetic 2D Panoramic X-Ray from a 3D CBCT volume.
Logic:
1. Fits a spline curve through the detected teeth centroids (The "Jaw Line").
2. Samples the 3D volume along this curve (Curved Planar Reformation - CPR).
3. Projects the sampled volume to 2D (MIP: Maximum Intensity Projection).
"""
import numpy as np
import cv2
from scipy.interpolate import splprep, splev
from scipy.ndimage import map_coordinates
import logging
import os

logger = logging.getLogger(__name__)

def generate_synthetic_pano(volume_data, teeth_segments, output_path):
    """
    Generates and saves a synthetic panoramic image.
    
    Args:
        volume_data: 3D numpy array (Z, Y, X)
        teeth_segments: List of tooth dicts with 'bbox_3d'
        output_path: Path to save the generated JPG
        
    Returns:
        bool: True if successful
    """
    try:
        if not teeth_segments:
            logger.warning("No teeth to generate pano curve.")
            return False

        points = []
        for t in teeth_segments:
            min_x, max_x, min_y, max_y, _, _ = t['bbox_3d']
            center_x = (min_x + max_x) // 2
            center_y = (min_y + max_y) // 2
            points.append([center_x, center_y])
            
        points = np.array(points)

        mean_center = points.mean(axis=0)
        angles = np.arctan2(points[:, 1] - mean_center[1], points[:, 0] - mean_center[0])
        sorted_indices = np.argsort(angles)
        points = points[sorted_indices]
        
        # 2. Fit Spline Curve (The "Jaw Line")
        # Need at least 4 points for cubic spline, fallback to linear if fewer
        if len(points) < 4:
            logger.warning("Not enough teeth for spline, using linear interpolation")
            k_val = 1
        else:
            k_val = 3 # Cubic spline
            
        # splprep needs unique points, add small jitter if duplicates exist
        points = points + np.random.normal(0, 0.1, points.shape)
        
        # Fit curve (x, y as function of parameter t)
        tck, u = splprep([points[:, 0], points[:, 1]], s=1000, k=k_val) # s=smoothing
        
        # 3. Create Curved Slice (Resampling)
        # Generate dense points along the curve
        # 2b. Calculate Arc Length for Aspect Ratio
        # Evaluate curve at high resolution to measure length
        u_temp = np.linspace(0, 1, 1000)
        x_rough, y_rough = splev(u_temp, tck)
        # Calculate segments length
        dx_r = np.diff(x_rough)
        dy_r = np.diff(y_rough)
        distances = np.sqrt(dx_r**2 + dy_r**2)
        arc_length = np.sum(distances)
        
        # Set Width based on Arc Length (1:1 pixel mapping)
        pano_width = int(arc_length)
        if pano_width < 100: pano_width = 100 # Min width safety
        
        logger.info(f"   📏 Calculated Arch Length: {arc_length:.1f} pixels. Output Width: {pano_width}")

        # 3. Create Curved Slice (Resampling)
        u_new = np.linspace(0, 1, pano_width)
        x_curve, y_curve = splev(u_new, tck)
        
        # --- DEBUG: Generate Axial Curve View ---
        try:
            # Axial MIP (Z-axis is index 2)
            axial_mip = np.mean(volume_data, axis=2) # Mean is clearer than Max for structure
            # Normalize
            vmin_ax, vmax_ax = np.percentile(axial_mip, [5, 99])
            axial_norm = np.clip((axial_mip - vmin_ax) / (vmax_ax - vmin_ax), 0, 1) * 255
            axial_img = cv2.cvtColor(axial_norm.astype(np.uint8), cv2.COLOR_GRAY2BGR)
            
            # Draw Points
            for p in points:
                cv2.circle(axial_img, (int(p[1]), int(p[0])), 5, (0, 0, 255), -1) # Note: CV2 uses (x,y) but numpy is (row,col)=(x,y) here? 
                # Wait, volume_data is (X, Y, Z). 
                # Axial view is (X, Y).
                # Dim 0 is X (rows?), Dim 1 is Y (cols?).
                # In plotting: imshow shows dim0 as Y-axis (rows), dim1 as X-axis (cols).
                # But here we used: points = [center_x, center_y]. 
                # center_x is index 0. center_y is index 1.
                # So if we plot:
                pass

            # Robust Visual: 
            # volume shape (X, Y, Z). 
            # Axial image shape (X, Y). T
            # If we assume X is width, Y is height of the slice.
            # CV2 coords are (width_idx, height_idx) -> (y, x).
            
            # Draw Curve
            curve_pts = np.column_stack((y_curve, x_curve)).astype(np.int32)
            cv2.polylines(axial_img, [curve_pts], False, (0, 255, 0), 2)
            
            # Draw Teeth
            for p in points:
                # p is (x, y). CV2 needs (y, x) for (col, row)
                cv2.circle(axial_img, (int(p[1]), int(p[0])), 8, (0, 0, 255), -1)

            debug_path = output_path.replace('.jpg', '_debug.jpg')
            cv2.imwrite(debug_path, axial_img)
            logger.info(f"   🖼️ Saved Debug Axial View: {debug_path}")
        except Exception as e:
            logger.warning(f"Failed to generate debug axial image: {e}")
        # ----------------------------------------
        
        # Define thickness (how deep into the jaw to look)
        # Standard OPG covers ~15-20mm. At 1.5mm/pixel, that's ~10-15 pixels.
        # But we want to be generous to catch tilted teeth. Let's use 60 pixels coverage.
        thickness = 60 
        num_samples = 30
        
        # Prepare target image buffer (Height x Width)
        # Nibabel loads as (X, Y, Z). Z is usually height (Superior-Inferior).
        x_dim, y_dim, z_dim = volume_data.shape
        pano_height = z_dim
        
        pano_image = np.zeros((pano_height, pano_width), dtype=np.float32)

        # 4. Sampling Loop (Average Intensity Projection - AIP)
        # Mimics X-ray attenuation (summation) rather than MIP (brightest vessel).
        
        logger.info(f"   🔄 Projecting 3D volume to 2D Pano (AIP). Vol Shape: {volume_data.shape}. Pano Size: {pano_width}x{pano_height}...")
        
        # Calculate gradients to find normals
        dx = np.gradient(x_curve)
        dy = np.gradient(y_curve)
        norms = np.hypot(dx, dy)
        norms[norms==0] = 1 # Avoid div/0
        
        nx = -dy / norms # Normal X
        ny = dx / norms  # Normal Y
        
        # Accumulate sum for Average Projection
        accumulated_projection = np.zeros((pano_height, pano_width), dtype=np.float32)
        
        # Sample at offsets (-thickness/2 to +thickness/2)
        for offset in np.linspace(-thickness/2, thickness/2, num_samples): 
            # Offset correlation
            x_sample = x_curve + nx * offset
            y_sample = y_curve + ny * offset
            
            # Create a coordinate grid for the whole "curtain"
            # We want to iterate Z for every point on the curve (pano_width)
            
            z_range = np.arange(z_dim)
            # zz corresponds to row index of pano (Height/Z), xx to col index (Width/Curve)
            zz, xx = np.meshgrid(z_range, np.arange(pano_width), indexing='ij') 
            
            # For map_coordinates (input rank 3: X, Y, Z), we need three coordinate arrays of same shape.
            # We want result shape (z_dim, pano_width).
            
            # X coordinate: varies with pano_width (xx), constant along Z
            # sample_coords_x shape should be (z_dim, pano_width)
            # x_sample is length pano_width.
            sample_coords_x = np.tile(x_sample, (z_dim, 1))
            
            # Y coordinate: varies with pano_width
            sample_coords_y = np.tile(y_sample, (z_dim, 1))
            
            # Z coordinate: varies with z_dim (zz), constant along pano_width
            # z_range is length z_dim
            sample_coords_z = np.tile(z_range.reshape(-1, 1), (1, pano_width))
            
            # Stack in order (X, Y, Z) because volume is (X, Y, Z)
            coords = np.stack([sample_coords_x, sample_coords_y, sample_coords_z])
            
            sampled_slice = map_coordinates(volume_data, coords, order=1, mode='nearest')
            
            accumulated_projection += sampled_slice
            
        # Compute Average
        accumulated_projection /= num_samples
        
        # Flip Z to match radiograph orientation (Top-Down)
        # Usually NIfTI Z=0 is bottom (feet/neck) and Z=Max is top (head).
        # We constructed 'pano_image' such that row 0 corresponds to Z=0.
        # Image row 0 is top. So currrently row 0 shows Neck. 
        # We need to flip UD to show Head at top.
        accumulated_projection = np.flipud(accumulated_projection)
        
        vmin, vmax = np.percentile(accumulated_projection, [5, 99])
        pano_norm = np.clip((accumulated_projection - vmin) / (vmax - vmin), 0, 1) * 255
        pano_uint8 = pano_norm.astype(np.uint8)
        
        # Enhance contrast (CLAHE)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        pano_enhanced = clahe.apply(pano_uint8)
        
        # Save Pano
        cv2.imwrite(output_path, pano_enhanced)
        logger.info(f"✅ Pano generated and saved to {output_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate pano: {e}")
        return False
