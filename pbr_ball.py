# pbr ball generation
import bpy
import os
import sys
script_dir = os.getcwd()    # get present working directory
sys.path += [script_dir]

from grass import deleteInitialObjects, setRenderingEngine, setRenderResolution, generateTurfField

def importFbxFiles(filepath=script_dir):
    balls = []
    if not filepath:
        return balls
    else:
        for bdir in os.listdir(os.path.join(filepath, 'textures', 'ball')):
            path = os.path.join(filepath, 'textures', 'ball', bdir)
            if os.path.isdir(path):
                color_f = os.path.join(path, '{}_color.png'.format(bdir))
                normal_f = os.path.join(path, '{}_normal.png'.format(bdir))
                coeff_f = os.path.join(path, '{}_coeff.png'.format(bdir))
                mesh_f = os.path.join(path, '{}_mesh.fbx'.format(bdir))
                balls.append((mesh_f,
                              bpy.data.images.load(color_f),
                              bpy.data.images.load(normal_f),
                              bpy.data.images.load(coeff_f)))
        return balls

# trent's code
def createPbrBall(roughness=0.05):

    # roughness = 0.05

    mat = bpy.data.materials.new('PBRBall')
    mat.use_nodes = True
    node_tree = mat.node_tree
    nodes = node_tree.nodes

    output = nodes['Material Output']


    roughness_value = nodes.new(type='ShaderNodeValue')
    roughness_value.name = roughness_value.label = 'Roughness'
    roughness_value.outputs[0].default_value = roughness

    # Textures
    color_tex = nodes.new(type='ShaderNodeTexImage')
    color_tex.name = color_tex.label = 'ColorTexture'

    normal_tex = nodes.new(type='ShaderNodeTexImage')
    normal_tex.color_space = 'NONE'
    normal_tex.name = normal_tex.label = 'NormalTexture'

    normal_tex_inv = nodes.new(type='ShaderNodeInvert')
    normal_tex_inv.name = normal_tex_inv.label = 'NormalTextureInvert'

    normal_map = nodes.new(type='ShaderNodeNormalMap')
    normal_map.name = normal_map.label = 'NormalMap'

    # Shaders
    glossy = nodes.new(type='ShaderNodeBsdfGlossy')
    glossy.inputs['Color'].default_value = (1.0, 1.0, 1.0, 1.0)
    glossy.name = glossy.label = 'Gloss'

    diffuse = nodes['Diffuse BSDF']
    diffuse.name = diffuse.label = 'Diffuse'

    mix = nodes.new(type='ShaderNodeMixShader')
    mix.name = mix.label = 'GlossDiffuseMix'

    # Fresnel group
    fresnel = nodes.new(type='ShaderNodeFresnel')
    fresnel.name = fresnel.label = 'Fresnel'

    fresnel_bump = nodes.new(type='ShaderNodeBump')
    fresnel_bump.name = fresnel_bump.label = 'FresnelBump'

    fresnel_geometry = nodes.new(type='ShaderNodeNewGeometry')
    fresnel_geometry.name = fresnel_geometry.label = 'FresnelGeometry'

    fresnel_mix = nodes.new(type='ShaderNodeMixRGB')
    fresnel_mix.name = fresnel_mix.label = 'FresnelMix'

    reflection_mix = nodes.new(type='ShaderNodeMixRGB')
    reflection_mix.inputs[1].default_value = (0.05, 0.05, 0.05, 0.05)
    reflection_mix.inputs[2].default_value = (1.0, 1.0, 1.0, 1.0)
    reflection_mix.name = reflection_mix.label = 'Reflectivity'

    # Link our final shaders
    node_tree.links.new(diffuse.outputs['BSDF'], mix.inputs[1])
    node_tree.links.new(glossy.outputs['BSDF'], mix.inputs[2])
    node_tree.links.new(mix.outputs['Shader'], output.inputs['Surface'])

    # Link our roughness
    node_tree.links.new(roughness_value.outputs[0], glossy.inputs['Roughness'])
    node_tree.links.new(roughness_value.outputs[0], diffuse.inputs['Roughness'])
    node_tree.links.new(roughness_value.outputs[0], fresnel_mix.inputs['Fac'])


    # Link our Fresnel group
    node_tree.links.new(fresnel_mix.outputs['Color'], fresnel.inputs['Normal'])
    node_tree.links.new(fresnel_bump.outputs['Normal'], fresnel_mix.inputs[1])
    node_tree.links.new(fresnel_geometry.outputs['Incoming'], fresnel_mix.inputs[2])
    node_tree.links.new(fresnel.outputs['Fac'], reflection_mix.inputs['Fac'])
    node_tree.links.new(reflection_mix.outputs['Color'], mix.inputs['Fac'])

    # Link our textures
    node_tree.links.new(color_tex.outputs['Color'], diffuse.inputs['Color'])

    node_tree.links.new(normal_tex.outputs['Color'], normal_tex_inv.inputs['Color'])
    node_tree.links.new(normal_tex_inv.outputs['Color'], normal_map.inputs['Color'])

    node_tree.links.new(normal_map.outputs['Normal'], diffuse.inputs['Normal'])
    node_tree.links.new(normal_map.outputs['Normal'], glossy.inputs['Normal'])
    node_tree.links.new(normal_map.outputs['Normal'], fresnel_bump.inputs['Normal'])

# from trent's code
def load_ball(ball):
    print(ball)
    path = ball[0]
    color = ball[1]
    normal = ball[2]
    coeff = ball[3]

    bpy.ops.import_scene.fbx(filepath=path)

    obj = bpy.context.selected_objects[0]
    obj.pass_index = 1  # for masking
    mat = bpy.data.materials['PBRBall']

    mat.node_tree.nodes['ColorTexture'].image = color
    mat.node_tree.nodes['NormalTexture'].image = normal

    obj.data.materials.append(mat)

    return obj

def crateShadowCatcher():
    pass

##################
# MAIN
##################

bpy.context.user_preferences.view.show_splash = False
deleteInitialObjects()
setRenderingEngine(samples=256) # faster render
setRenderResolution()

balls = importFbxFiles()
createPbrBall()
load_ball(balls[0])

field = generateTurfField()
