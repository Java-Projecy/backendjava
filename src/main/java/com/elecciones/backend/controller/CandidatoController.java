package com.elecciones.backend.controller;

import com.elecciones.backend.model.Candidato;
import com.elecciones.backend.service.CandidatoService;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.UUID;

@RestController
@RequestMapping("/data/candidates")
public class CandidatoController {

    private final CandidatoService service;

    public CandidatoController(CandidatoService service) {
        this.service = service;
    }

    @GetMapping
    public List<Candidato> getAll() {
        return service.getAll();
    }

    @GetMapping("/{id}")
    public ResponseEntity<Candidato> getById(@PathVariable UUID id) {
        return service.getById(id)
                .map(ResponseEntity::ok)
                .orElse(ResponseEntity.notFound().build());
    }

    @PostMapping
    public Candidato create(@RequestBody Candidato candidato) {
        return service.save(candidato);
    }

    @DeleteMapping("/{id}")
    public void delete(@PathVariable UUID id) {
        service.delete(id);
    }
    
}

